"""
Add these routes to your app.py file
"""

import os
from flask import request, jsonify
from datetime import datetime
import openai

# Configure OpenAI (add this near the top of app.py)
openai.api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key")

# Knowledge base about ClervIQ
CLERVIQ_KNOWLEDGE = """
ClervIQ is an AI-powered receptionist service that helps businesses manage calls, appointments, and customer communications.

Key Features:
- 24/7 AI phone answering
- Appointment scheduling
- Lead capture and qualification
- SMS and email follow-ups
- Integration with CRMs (Salesforce, HubSpot, GoHighLevel)
- Real-time analytics
- HIPAA compliant

Pricing:
- Starter: $299/month - Up to 500 calls
- Professional: $599/month - Up to 1,500 calls
- Enterprise: Custom pricing - Unlimited calls + white-glove support

Industries Served:
- Dental and Med Spas
- Real Estate
- Legal
- Finance
- Healthcare

How It Works:
1. Host your business phone number with us
2. AI answers calls instantly
3. Qualifies leads and books appointments
4. Integrates with your existing tools
5. You get real-time notifications and analytics
"""

# Chatbot endpoint
@chatbot_bp.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot messages with OpenAI"""
    try:
        data = request.json
        user_message = data.get('message', '')
        history = data.get('history', [])
        context = data.get('context', 'general')
        
        # Build conversation for OpenAI
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful sales assistant for ClervIQ, an AI receptionist service.
                
Current page context: {context}

{CLERVIQ_KNOWLEDGE}

Guidelines:
- Be friendly, professional, and concise
- Answer questions about ClervIQ's features, pricing, and how it works
- If asked about booking a demo, offer to collect their contact info
- If you don't know something, be honest and offer to connect them with the team
- Keep responses under 3 sentences unless explaining something complex
- Use emojis occasionally to be friendly
"""
            }
        ]
        
        # Add conversation history (last 10 messages)
        for msg in history[-10:]:
            messages.append({
                "role": "assistant" if msg['role'] == 'bot' else "user",
                "content": msg['content']
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Call OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or "gpt-3.5-turbo" for lower cost
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        
        bot_reply = response.choices[0].message.content
        
        # Check if we should collect lead info
        collect_lead = any(keyword in user_message.lower() for keyword in 
                          ['demo', 'pricing', 'contact', 'talk', 'call', 'schedule'])
        
        # Generate quick replies based on context
        quick_replies = []
        if context == 'pricing_page':
            quick_replies = ["💰 Compare plans", "📅 Book demo", "❓ FAQs"]
        elif context == 'homepage':
            quick_replies = ["🚀 How it works", "💰 Pricing", "📞 Contact sales"]
        elif 'pricing' in bot_reply.lower() or 'cost' in bot_reply.lower():
            quick_replies = ["💰 Show pricing", "📅 Schedule demo"]
        
        return jsonify({
            'success': True,
            'reply': bot_reply,
            'collect_lead': collect_lead,
            'quick_replies': quick_replies
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Save lead endpoint
@chatbot_bp.route('/api/save-lead', methods=['POST'])
def save_lead():
    """Save lead information from chatbot"""
    try:
        data = request.json
        name = data.get('name', '')
        email = data.get('email', '')
        conversation = data.get('conversation', [])
        
        # Save to database (you'll need to create a Leads table)
        conn = sqlite3.connect(os.path.join(app.instance_path, "users.db"))
        cur = conn.cursor()
        
        # Create leads table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                source TEXT,
                conversation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert lead
        cur.execute("""
            INSERT INTO leads (name, email, source, conversation)
            VALUES (?, ?, ?, ?)
        """, (name, email, 'chatbot', str(conversation)))
        
        conn.commit()
        conn.close()
        
        # Optional: Send notification email
        try:
            msg = Message(
                f"New Lead from Chatbot: {name}",
                sender=app.config['MAIL_USERNAME'],
                recipients=[app.config['MAIL_USERNAME']]
            )
            msg.body = f"""
New lead captured via chatbot:

Name: {name}
Email: {email}
Source: Website Chatbot

Conversation snippet:
{conversation[-3:] if len(conversation) > 3 else conversation}
"""
            mail.send(msg)
        except Exception as e:
            print(f"Email notification error: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Lead saved successfully'
        })
        
    except Exception as e:
        print(f"Save lead error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Simple fallback chatbot (if OpenAI not available)
@chatbot_bp.route('/api/chat-simple', methods=['POST'])
def chat_simple():
    """Simple rule-based chatbot without OpenAI"""
    try:
        data = request.json
        user_message = data.get('message', '').lower()
        
        # Simple keyword matching
        if any(word in user_message for word in ['pricing', 'cost', 'price', 'how much']):
            reply = "Our pricing starts at $299/month for up to 500 calls. We also offer Professional ($599/month) and Enterprise (custom) plans. Would you like to see a detailed comparison? 💰"
            quick_replies = ["📊 Compare plans", "📅 Book demo"]
            
        elif any(word in user_message for word in ['demo', 'trial', 'test']):
            reply = "I'd be happy to set up a demo! Could you share your name and email so our team can reach out? 📅"
            collect_lead = True
            quick_replies = []
            
        elif any(word in user_message for word in ['features', 'what', 'how']):
            reply = "ClervIQ provides 24/7 AI phone answering, appointment scheduling, lead qualification, and integrations with your CRM. We're perfect for dental, real estate, legal, and other service businesses! ✨"
            quick_replies = ["💰 Pricing", "📅 Book demo", "📞 How it works"]
            
        elif any(word in user_message for word in ['integrate', 'crm', 'calendar']):
            reply = "We integrate seamlessly with Salesforce, HubSpot, GoHighLevel, Google Calendar, and more! Our API makes it easy to connect with your existing tools. 🔌"
            quick_replies = ["See integrations", "Book demo"]
            
        elif any(word in user_message for word in ['hipaa', 'compliant', 'secure']):
            reply = "Yes! We're fully HIPAA compliant and take security seriously. All conversations are encrypted and we follow strict data protection standards. 🔒"
            quick_replies = ["Learn more", "Talk to sales"]
            
        else:
            reply = "Great question! I'm here to help you learn about ClervIQ's AI receptionist service. What would you like to know? 🤖"
            quick_replies = ["💰 Pricing", "⚙️ Features", "📅 Book demo"]
        
        collect_lead = 'demo' in user_message or 'contact' in user_message
        
        return jsonify({
            'success': True,
            'reply': reply,
            'collect_lead': collect_lead,
            'quick_replies': quick_replies
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
