// netlify/functions/submission-created.js
//
// Netlify automatically calls this function every time a Netlify Form
// on the site is submitted — no manual wiring needed, it just has to
// live at this exact path in the repo.
//
// It scores the "consultation" form for hot-lead criteria (price $800K+,
// timeline 6 months or less) and, if the visitor opted in to texts and
// gave a phone number, sends Ty an SMS via Twilio immediately.

exports.handler = async (event) => {
  try {
    const payload = JSON.parse(event.body).payload;

    // Only act on the consultation form (ignore any other forms on the site later)
    if (payload.form_name !== 'consultation') {
      return { statusCode: 200, body: 'ignored - not consultation form' };
    }

    const data = payload.data || {};
    const name = (data.name || 'Someone').trim();
    const phone = (data.phone || '').trim();
    const email = (data.email || '').trim();
    const intent = (data.intent || '').trim();
    const timeline = (data.timeline || '').trim();
    const priceRange = (data['price-range'] || '').trim();
    const smsConsent = data['sms-consent'] === 'yes';
    const message = (data.message || '').trim();

    const hotTimeline = ['ASAP - within 3 months', '3-6 months'].includes(timeline);
    const hotPrice = priceRange === '$800K+';
    const isHotLead = hotTimeline && hotPrice;

    console.log(
      `Submission from ${name}: intent=${intent}, timeline=${timeline}, price=${priceRange}, hot=${isHotLead}, smsConsent=${smsConsent}, hasPhone=${!!phone}`
    );

    // Only text if it's a hot lead, they consented to texts, and left a phone number
    if (isHotLead && smsConsent && phone) {
      const accountSid = process.env.TWILIO_ACCOUNT_SID;
      const authToken = process.env.TWILIO_AUTH_TOKEN;
      const fromNumber = process.env.TWILIO_PHONE_NUMBER;
      const toNumber = process.env.TY_NOTIFY_PHONE || '+14065449794';

      if (!accountSid || !authToken || !fromNumber) {
        console.error('Missing Twilio environment variables - cannot send SMS');
        return { statusCode: 200, body: 'hot lead but Twilio env vars missing' };
      }

      const body =
        `HOT LEAD: ${name} — ${intent || 'Buy/Sell'}, ${priceRange}, ` +
        `timeline ${timeline}. Phone: ${phone}${email ? ', Email: ' + email : ''}` +
        `${message ? '. Note: ' + message.slice(0, 120) : ''}`;

      const authHeader = 'Basic ' + Buffer.from(`${accountSid}:${authToken}`).toString('base64');
      const params = new URLSearchParams();
      params.append('To', toNumber);
      params.append('From', fromNumber);
      params.append('Body', body);

      const twilioResponse = await fetch(
        `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`,
        {
          method: 'POST',
          headers: {
            Authorization: authHeader,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: params.toString(),
        }
      );

      if (!twilioResponse.ok) {
        const errText = await twilioResponse.text();
        console.error('Twilio send failed:', twilioResponse.status, errText);
        return { statusCode: 200, body: 'hot lead but SMS send failed - check logs' };
      }

      console.log('Hot lead SMS sent successfully to', toNumber);
      return { statusCode: 200, body: 'hot lead SMS sent' };
    }

    return { statusCode: 200, body: 'submission logged, not a hot lead' };
  } catch (err) {
    console.error('submission-created function error:', err);
    // Always return 200 so Netlify doesn't retry-loop on a bad payload
    return { statusCode: 200, body: 'error logged' };
  }
};
