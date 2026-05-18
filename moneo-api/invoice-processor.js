/**
 * Invoice Processor Module
 * Orchestrates automated invoice creation from Clam inbox POs
 * Uses SQLite database on Atlas via EmailDatabaseClient for state management
 */

const MSGraphEmailManager = require('./msgraph-email-manager');
const QuickBooksManager = require('./quickbooks-manager');
const EmailDatabaseClient = require('./email-database-client');
const Anthropic = require('@anthropic-ai/sdk');
const logger = require('../utils/logger');
const { notify } = require('../utils/notify');
const { getDispatcher } = require('./alert-dispatcher');

class InvoiceProcessor {
  constructor(config) {
    this.config = config;
    this.clamEmailManager = null;
    this.qbManager = null;
    this.anthropic = null;

    this.db = null;

    // Test mode invoice counter
    this.testInvoiceCounter = 1;
  }

  async initialize() {
    logger.info('InvoiceProcessor', 'Initializing...');

    // Initialize database client (Atlas API)
    this.db = new EmailDatabaseClient();
    const health = await this.db.checkHealth();
    logger.info('InvoiceProcessor', `Database API connected: ${health.status}`);

    // Initialize Clam email manager
    this.clamEmailManager = new MSGraphEmailManager('clam');
    await this.clamEmailManager.init();

    // Initialize QuickBooks manager (GPJ-specific credentials file)
    const path = require('path');
    this.qbManager = new QuickBooksManager(
      path.join(__dirname, '../config/quickbooks-credentials-gpj.json')
    );
    await this.qbManager.init();

    // Initialize Anthropic
    this.anthropic = new Anthropic({
      apiKey: this.config.anthropicApiKey || process.env.ANTHROPIC_API_KEY
    });

    logger.info('InvoiceProcessor', 'Initialized successfully');
  }

  /**
   * Main processing loop - two phases:
   * 1. Sync: Fetch from MS Graph -> upsert into DB
   * 2. Process: Get unprocessed emails -> verify/extract/match -> create POs in DB
   */
  async processNewPOs() {
    logger.info('InvoiceProcessor', '=== Starting PO processing ===');

    const run = await this.db.startRun();
    let processed = 0;
    let drafted = 0;
    let pendingReview = 0;
    let failed = 0;
    let skipped = 0;
    let emailsSynced = 0;

    try {
      // === Phase 1: Sync emails from MS Graph to DB ===
      const emails = await this.clamEmailManager.getRecentEmails(50, true);
      logger.info('InvoiceProcessor', `Fetched ${emails.length} unread emails from MS Graph`);

      if (emails.length > 0) {
        const syncResult = await this.db.upsertEmailBatch(emails);
        emailsSynced = syncResult.synced;
        logger.info('InvoiceProcessor', `Synced ${emailsSynced} emails to database`);
      }

      // === Phase 2: Process unprocessed emails ===
      const unprocessed = await this.db.getUnprocessedEmails();
      logger.info('InvoiceProcessor', `${unprocessed.length} unprocessed emails in database`);

      for (const dbEmail of unprocessed) {
        try {
          // Build an email-like object for existing methods
          const email = {
            id: dbEmail.message_id,
            subject: dbEmail.subject || '',
            from: dbEmail.sender,
            bodyPreview: dbEmail.body_preview,
            hasAttachments: !!dbEmail.has_attachments
          };

          let result;

          if (email.hasAttachments) {
            // Has attachments - send directly to processing (PDF extraction)
            result = await this.processSinglePO(email, dbEmail.id);
          } else {
            // No attachments - let Claude verify if it's a PO
            const isPO = await this.verifyIsPurchaseOrder(email);
            if (!isPO) {
              await this.db.classifyEmail(dbEmail.message_id, false);
              skipped++;
              continue;
            }
            // Claude says yes - send to processing (body extraction)
            result = await this.processSinglePO(email, dbEmail.id);
          }

          if (result.status === 'skipped') {
            await this.db.classifyEmail(dbEmail.message_id, false);
            skipped++;
          } else {
            await this.db.classifyEmail(dbEmail.message_id, true);
            processed++;

            if (result.status === 'drafted') {
              drafted++;
            } else if (result.status === 'pending_review' || result.status === 'manual_review') {
              pendingReview++;
            } else if (result.status === 'failed') {
              failed++;
            }
          }

        } catch (error) {
          logger.error('InvoiceProcessor', 'Error processing email', {
            messageId: dbEmail.message_id,
            subject: dbEmail.subject,
            error: error.message
          });
          // Classify as processed to avoid re-processing on error
          await this.db.classifyEmail(dbEmail.message_id, false);
          failed++;
        }
      }

      // Complete the run
      await this.db.completeRun(run.id, {
        emails_fetched: emails.length,
        emails_synced: emailsSynced,
        pos_extracted: processed,
        invoices_drafted: drafted,
        pending_review: pendingReview,
        failed,
        skipped
      });

      // Send Discord notification
      if (processed > 0 && this.discord) {
        await this.sendDiscordNotification({ processed, drafted, pendingReview, failed });
      }

      // Phase 3: dispatch Oracle alert for Clam POs (speaks immediately)
      if (drafted > 0) {
        try {
          const poWord = drafted === 1 ? 'PO' : 'POs';
          await getDispatcher().dispatch({
            severity: 'critical',
            source: 'clam-po',
            title: `${drafted} Clam ${poWord} drafted`,
            message: pendingReview > 0 ? `${pendingReview} also need review.` : '',
            spokenMessage: drafted === 1
              ? `New Clam PO landed and a draft invoice is ready for approval.`
              : `${drafted} new Clam POs landed. Draft invoices are ready for approval.`,
            alertId: `clam-po-batch-${Date.now()}`,
          });
        } catch (e) {
          logger.warn('InvoiceProcessor', 'Oracle alert dispatch failed (non-fatal)', { error: e.message });
        }
      }

      logger.info('InvoiceProcessor', '=== Processing complete ===', {
        processed, drafted, pendingReview, failed, skipped
      });

      return { processed, drafted, pendingReview, failed, skipped };

    } catch (error) {
      logger.error('InvoiceProcessor', 'Processing loop failed', { error: error.message });
      // Try to complete the run with error info
      try {
        await this.db.completeRun(run.id, {
          emails_fetched: 0, emails_synced: emailsSynced, pos_extracted: processed,
          invoices_drafted: drafted, pending_review: pendingReview, failed: failed + 1, skipped
        });
      } catch (e) { /* ignore */ }
      throw error;
    }
  }

  /**
   * Check if this PO has already been processed
   * Uses database lookups instead of in-memory arrays
   */
  async isDuplicate(email) {
    // Check if email ID already exists in DB
    const existing = await this.db.getEmailByMessageId(email.id);
    if (existing && existing.is_purchase_order !== null) {
      return true;
    }

    // Check PO number from subject
    const poNumberMatch = email.subject.match(/(?:PO|Purchase Order|P)\s*[#:-]?\s*([A-Z0-9-]+)/i);
    if (poNumberMatch) {
      const poNumber = poNumberMatch[1];
      const existingPOs = await this.db.getPOByNumber(poNumber);
      if (existingPOs && existingPOs.length > 0) {
        logger.info('InvoiceProcessor', `PO number ${poNumber} already processed`);
        return true;
      }
    }

    return false;
  }

  /**
   * Quick verification using Claude to determine if email is actually a purchase order
   */
  async verifyIsPurchaseOrder(email) {
    try {
      const prompt = `Is this email a purchase order (PO) from a customer requesting products to be shipped?

Subject: ${email.subject}
From: ${email.from}
Preview: ${email.bodyPreview}

Answer with ONLY "yes" or "no".

A purchase order typically:
- Contains item descriptions, quantities, and prices
- Has shipping address
- Includes PO number or order number
- Is requesting products to be shipped

NOT a purchase order:
- Promotional emails, surveys, feedback requests
- Shipping confirmations or tracking updates
- Account setup or verification emails
- Re: or Fwd: messages (replies/forwards)`;

      const response = await this.anthropic.messages.create({
        model: 'claude-sonnet-4-5-20250929',
        max_tokens: 10,
        messages: [{
          role: 'user',
          content: prompt
        }]
      });

      const answer = response.content[0].text.trim().toLowerCase();
      return answer === 'yes';

    } catch (error) {
      logger.error('InvoiceProcessor', 'PO verification failed', { error: error.message });
      return true;
    }
  }

  /**
   * Process a single PO email
   * @param {Object} email - Email-like object with id, subject, from, bodyPreview, hasAttachments
   * @param {number} dbEmailId - Internal DB email row ID for linking POs
   */
  async processSinglePO(email, dbEmailId) {
    logger.info('InvoiceProcessor', `Processing PO: ${email.subject}`);

    try {
      // Step 0: Quick verification
      const isPO = email.hasAttachments || await this.verifyIsPurchaseOrder(email);
      if (!isPO) {
        logger.info('InvoiceProcessor', `Not a purchase order, skipping: ${email.subject}`);
        return { status: 'skipped', reason: 'Not a purchase order' };
      }

      let poData = null;
      let extractionMethod = null;

      // Step 1: Try PDF attachment first
      if (email.hasAttachments) {
        const pdfAttachment = await this.clamEmailManager.getPDFAttachment(email.id);
        if (pdfAttachment) {
          logger.info('InvoiceProcessor', 'Found PDF attachment, extracting data...');
          poData = await this.extractPOData(pdfAttachment);
          extractionMethod = 'pdf';
        }
      }

      // Step 2: If no PDF or extraction failed, try email body
      if (!poData || !poData.poNumber) {
        logger.info('InvoiceProcessor', 'Trying to extract PO from email body...');
        poData = await this.extractPOFromEmailBody(email);
        extractionMethod = 'body';
      }

      // Step 3: If still no data, create manual review PO in DB
      if (!poData || !poData.poNumber) {
        logger.warn('InvoiceProcessor', 'Could not extract PO data - adding to manual review');

        const po = await this.db.createPurchaseOrder({
          email_id: dbEmailId,
          po_number: null,
          company_name: 'MANUAL REVIEW REQUIRED',
          order_date: new Date().toISOString().split('T')[0],
          line_items: [],
          total_amount: 0,
          shipping_address: null,
          terms: null,
          sales_rep: null,
          extraction_method: 'manual',
          status: 'manual_review',
          error_message: 'Could not parse PO data automatically'
        });

        return { status: 'manual_review', poId: po.id };
      }

      logger.info('InvoiceProcessor', `Extracted PO data via ${extractionMethod}`, {
        poNumber: poData.poNumber,
        company: poData.companyName
      });

      // Step 4: Match customer in QuickBooks
      const matchResult = await this.matchCustomer(poData.companyName, poData.shippingAddress);

      // Create purchase order in DB
      const po = await this.db.createPurchaseOrder({
        email_id: dbEmailId,
        po_number: poData.poNumber,
        company_name: poData.companyName,
        order_date: poData.orderDate,
        line_items: poData.lineItems,
        total_amount: poData.totalAmount,
        shipping_address: poData.shippingAddress,
        terms: poData.terms,
        sales_rep: poData.salesRep || null,
        extraction_method: extractionMethod,
        status: 'pending',
        qb_customer_id: matchResult ? matchResult.customer.Id : null,
        qb_customer_name: matchResult ? matchResult.customer.DisplayName : null,
        match_confidence: matchResult ? matchResult.confidence / 100 : null,
        ship_via: poData.shipVia || null,
        freight_terms: poData.freightTerms || null,
        freight_account_number: poData.freightAccountNumber || null,
        fob: poData.fob || null,
        billing_method: this.deriveBillingMethod(poData)
      });

      if (matchResult && matchResult.customer) {
        logger.info('InvoiceProcessor', `Customer match: ${poData.companyName} -> ${matchResult.customer.DisplayName} (${matchResult.confidence}% confidence)`);
      } else {
        logger.info('InvoiceProcessor', `No customer match found for: ${poData.companyName}`);
      }

      return { status: 'pending_review', poId: po.id };

    } catch (error) {
      logger.error('InvoiceProcessor', 'Failed to process PO', {
        emailId: email.id,
        subject: email.subject,
        error: error.message
      });

      // Record failure in DB
      try {
        await this.db.createPurchaseOrder({
          email_id: dbEmailId,
          po_number: null,
          company_name: null,
          status: 'failed',
          extraction_method: null,
          error_message: error.message
        });
      } catch (e) { /* ignore secondary error */ }

      return { status: 'failed', error: error.message };
    }
  }

  /**
   * Derive freight billing method from extracted shipping fields.
   * Conservative: auto-derive only for exact "UPS COLLECT" or "BEST WAY".
   * Everything else → review_required. See memory: gpj-shipping-billing-rules.md
   */
  deriveBillingMethod(poData) {
    const shipVia = (poData.shipVia || '').toUpperCase().trim();
    const totalQty = Array.isArray(poData.lineItems)
      ? poData.lineItems.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0)
      : 0;

    if (shipVia.includes('UPS COLLECT')) return 'collect';
    if (shipVia.includes('BEST WAY')) return totalQty >= 150 ? 'ffa' : 'prepaid_and_add';
    return 'review_required';
  }

  /**
   * Extract PO data from PDF using Claude
   */
  async extractPOData(pdfAttachment) {
    const prompt = `Extract purchase order data from this document and return as JSON:

{
  "poNumber": "string",
  "companyName": "string",
  "orderDate": "YYYY-MM-DD",
  "lineItems": [
    {
      "description": "string",
      "quantity": number,
      "unitPrice": number,
      "amount": number
    }
  ],
  "totalAmount": number,
  "shippingAddress": "string",
  "terms": "string (payment terms, e.g. NET 30, 2% 10TH PROX)",
  "salesRep": "string (name of sales representative or account manager, or null if not found)",
  "shipVia": "string (raw 'Ship Via' value verbatim, e.g. 'BEST WAY', 'UPS COLLECT', 'UPS GROUND', or null)",
  "freightTerms": "string (raw 'Freight Terms' or 'Freight Ref' value, e.g. 'Collect', 'Prepaid', '3rd Party', or null)",
  "freightAccountNumber": "string (carrier account number if explicitly shown on PO — usually only for Collect shipments, or null)",
  "fob": "string (F.O.B. field value, e.g. 'Origin', 'Destination', 'ERIE', or null if blank)"
}

Extract shipping fields verbatim — do not interpret or infer. If a field is blank on the PO, return null.

Return ONLY the JSON object, no other text.`;

    const response = await this.anthropic.messages.create({
      model: 'claude-sonnet-4-5-20250929',
      max_tokens: 4096,
      messages: [{
        role: 'user',
        content: [
          {
            type: 'document',
            source: {
              type: 'base64',
              media_type: 'application/pdf',
              data: pdfAttachment.contentBytes
            }
          },
          {
            type: 'text',
            text: prompt
          }
        ]
      }]
    });

    let jsonText = response.content[0].text.trim();

    if (jsonText.startsWith('```')) {
      jsonText = jsonText.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '').trim();
    }

    return JSON.parse(jsonText);
  }

  /**
   * Extract PO data from email body text using Claude
   */
  async extractPOFromEmailBody(email) {
    try {
      const fullEmail = await this.clamEmailManager.getEmailDetails(email.id);
      const emailBody = fullEmail.body || email.bodyPreview || '';

      if (!emailBody || emailBody.length < 50) {
        logger.warn('InvoiceProcessor', 'Email body too short or empty');
        return null;
      }

      const prompt = `Extract purchase order data from this email and return as JSON:

{
  "poNumber": "string",
  "companyName": "string",
  "orderDate": "YYYY-MM-DD",
  "lineItems": [
    {
      "description": "string",
      "quantity": number,
      "unitPrice": number,
      "amount": number
    }
  ],
  "totalAmount": number,
  "shippingAddress": "string",
  "terms": "string (payment terms)",
  "salesRep": "string (name of sales representative or account manager, or null if not found)",
  "shipVia": "string (raw 'Ship Via' value verbatim, e.g. 'BEST WAY', 'UPS COLLECT', or null)",
  "freightTerms": "string (raw 'Freight Terms' value, e.g. 'Collect', 'Prepaid', or null)",
  "freightAccountNumber": "string (carrier account number if explicitly shown, or null)",
  "fob": "string (F.O.B. value, or null if blank)"
}

Extract shipping fields verbatim — do not interpret. If blank, return null.

Email content:
${emailBody}

Return ONLY the JSON object, no other text. If you cannot extract valid PO data, return null.`;

      const response = await this.anthropic.messages.create({
        model: 'claude-sonnet-4-5-20250929',
        max_tokens: 4096,
        messages: [{
          role: 'user',
          content: prompt
        }]
      });

      let jsonText = response.content[0].text.trim();

      if (jsonText === 'null' || jsonText === 'NULL') {
        return null;
      }

      if (jsonText.startsWith('```')) {
        jsonText = jsonText.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '').trim();
      }

      const poData = JSON.parse(jsonText);

      if (!poData.poNumber || !poData.lineItems || poData.lineItems.length === 0) {
        return null;
      }

      return poData;
    } catch (error) {
      logger.error('InvoiceProcessor', 'Failed to extract PO from email body', { error: error.message });
      return null;
    }
  }

  /**
   * Smart customer matching with fuzzy string comparison
   * For Ferguson/Hajoca: matches by branch number from shipping address
   */
  async matchCustomer(companyName, shippingAddress) {
    if (!companyName) return null;

    const allCustomers = await this.qbManager.getAllCustomers();

    if (!allCustomers || allCustomers.length === 0) {
      logger.warn('InvoiceProcessor', 'No customers found in QuickBooks');
      return null;
    }

    // Ferguson/Hajoca: match by branch number from shipping address
    const normalizedCompany = companyName.toLowerCase();
    if (normalizedCompany.includes('ferguson') || normalizedCompany.includes('hajoca')) {
      const branchResult = this.matchBranch(companyName, shippingAddress, allCustomers);
      if (branchResult) {
        logger.info('InvoiceProcessor', `Branch match: ${companyName} -> ${branchResult.customer.DisplayName} (${branchResult.confidence}%, via ${branchResult.matchMethod})`);
        return branchResult;
      }
      logger.warn('InvoiceProcessor', `No branch match for ${companyName}, falling back to fuzzy match`);
    }

    // Standard fuzzy matching for other customers
    const stringSimilarity = require('string-similarity');
    const normalizedInput = companyName.toLowerCase().trim();

    const matches = allCustomers.map(customer => {
      const customerName = customer.DisplayName.toLowerCase().trim();
      const similarity = stringSimilarity.compareTwoStrings(normalizedInput, customerName);
      const exactMatch = normalizedInput === customerName ? 1.0 : 0;
      const substringMatch = customerName.includes(normalizedInput) || normalizedInput.includes(customerName) ? 0.1 : 0;
      const confidence = Math.min(100, Math.round((similarity + exactMatch + substringMatch) * 100));

      return { customer, confidence, similarity };
    });

    matches.sort((a, b) => b.confidence - a.confidence);
    const bestMatch = matches[0];

    logger.info('InvoiceProcessor', `Customer matching: ${companyName}`, {
      bestMatch: bestMatch.customer.DisplayName,
      confidence: bestMatch.confidence,
      topMatches: matches.slice(0, 3).map(m => ({
        name: m.customer.DisplayName,
        confidence: m.confidence
      }))
    });

    return {
      customer: bestMatch.customer,
      confidence: bestMatch.confidence
    };
  }

  /**
   * Match Ferguson/Hajoca by branch number extracted from shipping address or company name
   */
  matchBranch(companyName, shippingAddress, allCustomers) {
    // Extract branch number from company name or shipping address
    const branchMatch = (companyName || '').match(/#(\d+)/) || (shippingAddress || '').match(/#(\d+)/);
    const branchNumber = branchMatch ? branchMatch[1] : null;

    const isFerguson = companyName.toLowerCase().includes('ferguson');
    const isHajoca = companyName.toLowerCase().includes('hajoca');

    // Filter to just Ferguson or Hajoca customers
    const vendorCustomers = allCustomers.filter(c => {
      const name = c.DisplayName.toLowerCase();
      return isFerguson ? name.includes('ferguson') : name.includes('hajoca');
    });

    // Try branch number match first
    if (branchNumber) {
      const match = vendorCustomers.find(c => c.DisplayName.includes(`#${branchNumber}`));
      if (match) {
        return { customer: match, confidence: 95, matchMethod: 'branch_number' };
      }
    }

    // Try city/state match from shipping address
    const cityStateMatch = (shippingAddress || '').match(/([^,]+),\s*([A-Z]{2})\s+\d{5}/);
    if (cityStateMatch) {
      const city = cityStateMatch[1].trim().toLowerCase();
      const state = cityStateMatch[2];

      const match = vendorCustomers.find(c => {
        const shipAddr = c.ShipAddr;
        if (!shipAddr) return false;
        return shipAddr.City?.toLowerCase() === city && shipAddr.CountrySubDivisionCode === state;
      });

      if (match) {
        return { customer: match, confidence: 85, matchMethod: 'ship_address' };
      }
    }

    // Fall back to parent/HQ company
    const hqMatch = vendorCustomers.find(c => c.DisplayName.toLowerCase().includes('(hq)'));
    if (hqMatch) {
      return { customer: hqMatch, confidence: 60, matchMethod: 'parent_company' };
    }

    return null;
  }

  /**
   * Create draft invoice in QuickBooks
   */
  async createDraftInvoice(customer, poData) {
    const totalQuantity = poData.lineItems.reduce((sum, item) => sum + (item.quantity || 0), 0);
    const shippingMethod = totalQuantity >= 150 ? 'FFA' : 'UPS';

    const testInvoiceNumber = `AI-Test-${this.testInvoiceCounter}`;
    this.testInvoiceCounter++;

    const invoiceData = {
      customerId: customer.Id,
      customerName: customer.DisplayName,
      lineItems: poData.lineItems,
      poNumber: poData.poNumber,
      dueDate: null,
      terms: null,
      shippingMethod: shippingMethod,
      docNumber: testInvoiceNumber
    };

    logger.info('InvoiceProcessor', `Creating invoice with shipping method: ${shippingMethod} (${totalQuantity} units)`);

    const invoice = await this.qbManager.createDraftInvoice(invoiceData);
    return invoice;
  }

  /**
   * Get current stats from database
   */
  async getStats() {
    return await this.db.getStats();
  }

  /**
   * Get review queue items from database
   */
  async getReviewQueue() {
    return await this.db.getPendingReview();
  }

  /**
   * Approve a review queue item and create invoice
   */
  async approveReviewItem(poId, qbCustomerName) {
    const po = await this.db.getPOById(poId);

    if (!po) {
      throw new Error(`Purchase order not found: ${poId}`);
    }

    // Find customer in QB
    const customers = await this.qbManager.searchCustomers(qbCustomerName);

    if (customers.length === 0) {
      throw new Error(`Customer not found in QuickBooks: ${qbCustomerName}`);
    }

    const customer = customers[0];

    // Reconstruct poData from DB record
    const poData = {
      poNumber: po.po_number,
      lineItems: typeof po.line_items === 'string' ? JSON.parse(po.line_items) : po.line_items,
      totalAmount: po.total_amount,
      shippingAddress: po.shipping_address,
      terms: po.terms
    };

    // Create invoice
    const invoice = await this.createDraftInvoice(customer, poData);

    // Update PO in DB
    await this.db.updatePOStatus(poId, 'drafted', {
      qb_customer_id: customer.Id,
      qb_customer_name: customer.DisplayName,
      qb_invoice_id: invoice.id || invoice.Id,
      qb_invoice_number: invoice.number || invoice.DocNumber
    });

    logger.info('InvoiceProcessor', 'Review item approved and invoice created', {
      poId,
      invoiceId: invoice.id || invoice.Id,
      customer: customer.DisplayName
    });

    return {
      invoiceId: invoice.id || invoice.Id,
      invoiceNumber: invoice.number || invoice.DocNumber,
      customerName: customer.DisplayName
    };
  }

  /**
   * Send Discord notification about processed POs
   */
  async sendDiscordNotification(results) {
    const { processed, drafted, pendingReview, failed } = results;
    if (processed === 0) return;

    const parts = [];
    if (drafted > 0) parts.push(`${drafted} drafted`);
    if (pendingReview > 0) parts.push(`${pendingReview} pending review`);
    if (failed > 0) parts.push(`${failed} failed`);

    await notify('auto-quote', {
      title: 'Clam Order Processing',
      message: parts.join(', ') + ` (${processed} total)`,
      severity: failed > 0 ? 'warning' : 'info',
      fields: [
        ...(drafted > 0 ? [{ name: 'Drafted', value: `${drafted}`, inline: true }] : []),
        ...(pendingReview > 0 ? [{ name: 'Review', value: `${pendingReview}`, inline: true }] : []),
        ...(failed > 0 ? [{ name: 'Failed', value: `${failed}`, inline: true }] : []),
      ]
    });
  }
}

module.exports = InvoiceProcessor;
