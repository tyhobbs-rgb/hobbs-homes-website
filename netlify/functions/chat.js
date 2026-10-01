// netlify/functions/chat.js
//
// Server-side proxy to the Claude API. Keeps the API key off the public
// page. The widget sends the running conversation each time (the API
// itself has no memory between calls), and this function asks Claude to
// both reply conversationally AND call a tool to report what it has
// learned so far about the visitor (intent, timeline, price range).
//
// When the widget sees intent + timeline + price range are all filled
// in, it shows a small "leave your info" card instead of asking Claude
// to keep guessing - phone numbers and consent checkboxes are handled
// by real form fields, not by the model, to keep the SMS consent
// evidence clean.

const SYSTEM_PROMPT = `You are the on-site assistant for Hobbs Homes, a real estate and new construction business run by Ty Hobbs in Missoula, Montana. Ty is direct, competitive, and no-BS - not folksy. Match that tone: short sentences, no fluff, no "As an AI" disclaimers.

Your only job is to have a short, natural conversation that figures out three things about the visitor:
1. Whether they're looking to buy, sell, both, or are just browsing
2. Their price range (roughly - doesn't need to be exact)
3. Their timeline (ASAP/within 3 months, 3-6 months, 6-12 months, or just exploring)

Ask ONE question at a time. Keep replies to 1-3 sentences. Don't be pushy, but keep the conversation moving toward those three answers.

Tone: direct and no-BS, but not cold. Before each question, briefly acknowledge what they just said - a few words, not a paragraph - so it reads like a real back-and-forth, not a form being filled out one field at a time. For example, if they say "buying," don't jump straight to "what's your price range" with nothing in between - something like "Nice, let's narrow it down - what's your price range?" lands better. Keep the acknowledgment short; the goal is warmth without losing momentum or sounding scripted.

Once you have all three, say something like "Got it - I'll get your info to Ty so he can follow up" and stop asking further questions. Do not ask for their name, phone, or email yourself - a form will handle that next.

EVERY response you give must include BOTH of these, every single time, no exceptions:
1. A short spoken reply (1-3 sentences) that will be shown directly to the visitor in the chat
2. A call to the update_lead tool, filling in whatever you've learned so far (leave fields blank if not yet known)

Never respond with only a tool call and no spoken text - the visitor needs to see a reply every time or the conversation looks broken. The tool call is invisible bookkeeping; the spoken reply is the actual conversation.`;

const TOOL = {
  name: 'update_lead',
  description: 'Record what has been learned about the visitor so far in this conversation. Call this on every turn, even if nothing new was learned - just repeat the previous values.',
  input_schema: {
    type: 'object',
    properties: {
      intent: {
        type: 'string',
        enum: ['Buy', 'Sell', 'Both', 'Just researching', ''],
        description: 'What the visitor is looking to do, or empty string if unknown',
      },
      timeline: {
        type: 'string',
        enum: ['ASAP - within 3 months', '3-6 months', '6-12 months', 'Just exploring', ''],
        description: 'Their timeframe, or empty string if unknown',
      },
      price_range: {
        type: 'string',
        enum: ['Under $500K', '$500K-$800K', '$800K+', 'Not sure yet', ''],
        description: 'Their rough price range, or empty string if unknown',
      },
      ready_for_contact: {
        type: 'boolean',
        description: 'True once intent, timeline, and price_range are all known and it is time to collect their contact info',
      },
    },
    required: ['intent', 'timeline', 'price_range', 'ready_for_contact'],
  },
};

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }

  try {
    const { messages } = JSON.parse(event.body);

    if (!Array.isArray(messages) || messages.length === 0) {
      return { statusCode: 400, body: JSON.stringify({ error: 'messages array required' }) };
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      console.error('Missing ANTHROPIC_API_KEY environment variable');
      return { statusCode: 500, body: JSON.stringify({ error: 'server not configured' }) };
    }

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 400,
        system: SYSTEM_PROMPT,
        tools: [TOOL],
        messages: messages,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error('Claude API error:', response.status, errText);
      return { statusCode: 502, body: JSON.stringify({ error: 'upstream error' }) };
    }

    const data = await response.json();

    let replyText = '';
    let leadState = null;

    for (const block of data.content || []) {
      if (block.type === 'text') {
        replyText += block.text;
      } else if (block.type === 'tool_use' && block.name === 'update_lead') {
        leadState = block.input;
      }
    }

    // Safety net: if Claude somehow returns only a tool call with no text,
    // never show the visitor a blank message.
    const finalReply = replyText.trim() || "Got it - tell me a bit more?";

    return {
      statusCode: 200,
      body: JSON.stringify({ reply: finalReply, leadState }),
    };
  } catch (err) {
    console.error('chat function error:', err);
    return { statusCode: 500, body: JSON.stringify({ error: 'internal error' }) };
  }
};
