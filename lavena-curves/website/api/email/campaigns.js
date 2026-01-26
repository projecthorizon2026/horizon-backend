// Brevo Email Campaigns API
// Docs: https://developers.brevo.com/reference/createemailcampaign

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const apiKey = process.env.BREVO_API_KEY;

  if (!apiKey) {
    return res.status(500).json({ error: 'Email service not configured. Add BREVO_API_KEY.' });
  }

  const headers = {
    'accept': 'application/json',
    'api-key': apiKey,
    'content-type': 'application/json'
  };

  try {
    // GET - List campaigns or get single campaign
    if (req.method === 'GET') {
      const { id, type = 'classic', status, limit = 20, offset = 0 } = req.query;

      if (id) {
        // Get single campaign with stats
        const [campaignRes, statsRes] = await Promise.all([
          fetch(`https://api.brevo.com/v3/emailCampaigns/${id}`, { headers }),
          fetch(`https://api.brevo.com/v3/emailCampaigns/${id}/statistics`, { headers })
        ]);

        const campaign = await campaignRes.json();
        const stats = statsRes.ok ? await statsRes.json() : null;

        return res.status(200).json({ ...campaign, statistics: stats });
      }

      // List campaigns
      let url = `https://api.brevo.com/v3/emailCampaigns?type=${type}&limit=${limit}&offset=${offset}`;
      if (status) url += `&status=${status}`;

      const response = await fetch(url, { headers });
      const data = await response.json();
      return res.status(200).json(data);
    }

    // POST - Create campaign or send
    if (req.method === 'POST') {
      const {
        action,
        id,
        name,
        subject,
        sender,
        htmlContent,
        listIds,
        scheduledAt,
        replyTo,
        tag
      } = req.body;

      // Send existing campaign
      if (action === 'send' && id) {
        const response = await fetch(`https://api.brevo.com/v3/emailCampaigns/${id}/sendNow`, {
          method: 'POST',
          headers
        });

        if (!response.ok) {
          const error = await response.json();
          return res.status(response.status).json(error);
        }

        return res.status(200).json({ success: true, message: 'Campaign sent!' });
      }

      // Schedule existing campaign
      if (action === 'schedule' && id && scheduledAt) {
        const response = await fetch(`https://api.brevo.com/v3/emailCampaigns/${id}/schedule`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ scheduledAt })
        });

        if (!response.ok) {
          const error = await response.json();
          return res.status(response.status).json(error);
        }

        return res.status(200).json({ success: true, message: 'Campaign scheduled!' });
      }

      // Send test email
      if (action === 'test' && id) {
        const { testEmails } = req.body;
        const response = await fetch(`https://api.brevo.com/v3/emailCampaigns/${id}/sendTest`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ emailTo: testEmails })
        });

        if (!response.ok) {
          const error = await response.json();
          return res.status(response.status).json(error);
        }

        return res.status(200).json({ success: true, message: 'Test email sent!' });
      }

      // Create new campaign
      if (!name || !subject || !htmlContent) {
        return res.status(400).json({ error: 'Missing required fields: name, subject, htmlContent' });
      }

      const campaignPayload = {
        name,
        subject,
        sender: sender || { name: 'Lumière Curves', email: 'hello@lumierecurves.shop' },
        type: 'classic',
        htmlContent,
        recipients: { listIds: listIds || [] },
        ...(replyTo && { replyTo }),
        ...(tag && { tag }),
        ...(scheduledAt && { scheduledAt })
      };

      const response = await fetch('https://api.brevo.com/v3/emailCampaigns', {
        method: 'POST',
        headers,
        body: JSON.stringify(campaignPayload)
      });

      const data = await response.json();

      if (!response.ok) {
        return res.status(response.status).json(data);
      }

      return res.status(201).json({
        success: true,
        campaignId: data.id,
        message: 'Campaign created successfully'
      });
    }

    // PUT - Update campaign
    if (req.method === 'PUT') {
      const { id, ...updates } = req.body;

      if (!id) {
        return res.status(400).json({ error: 'Campaign ID is required' });
      }

      const response = await fetch(`https://api.brevo.com/v3/emailCampaigns/${id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(updates)
      });

      if (!response.ok) {
        const error = await response.json();
        return res.status(response.status).json(error);
      }

      return res.status(200).json({ success: true, message: 'Campaign updated' });
    }

    // DELETE - Delete campaign
    if (req.method === 'DELETE') {
      const { id } = req.body;

      if (!id) {
        return res.status(400).json({ error: 'Campaign ID is required' });
      }

      const response = await fetch(`https://api.brevo.com/v3/emailCampaigns/${id}`, {
        method: 'DELETE',
        headers
      });

      if (!response.ok && response.status !== 204) {
        const error = await response.json();
        return res.status(response.status).json(error);
      }

      return res.status(200).json({ success: true, message: 'Campaign deleted' });
    }

    return res.status(405).json({ error: 'Method not allowed' });

  } catch (error) {
    console.error('Campaigns API error:', error);
    res.status(500).json({ error: error.message });
  }
}
