"""
Password reset functionality
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import os

password_reset_bp = Blueprint('password_reset', __name__)

# Serializer for generating secure tokens
def get_serializer():
    from app import app
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])

def send_reset_email(email, reset_url):
    """Send password reset email"""
    from app import mail
    
    msg = Message(
        "ClervIQ - Password Reset Request",
        sender=os.getenv('MAIL_USERNAME', 'noreply@clerviq.com'),
        recipients=[email]
    )
    
    msg.html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0a0e27; color: #e8f0ff; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: rgba(20, 30, 60, 0.8); border-radius: 20px; padding: 40px; border: 1px solid rgba(0, 212, 255, 0.2);">
            <h1 style="color: #00d4ff; text-align: center; margin-bottom: 30px;">🔐 Password Reset</h1>
            
            <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                You requested a password reset for your ClervIQ account.
            </p>
            
            <p style="font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                Click the button below to reset your password. This link expires in 1 hour.
            </p>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="{reset_url}" 
                   style="background: linear-gradient(135deg, #00d4ff 0%, #0080ff 100%); 
                          color: white; 
                          padding: 15px 40px; 
                          text-decoration: none; 
                          border-radius: 10px; 
                          font-size: 18px; 
                          font-weight: bold;
                          display: inline-block;">
                    Reset Password
                </a>
            </div>
            
            <p style="font-size: 14px; color: rgba(255, 255, 255, 0.6); margin-top: 30px;">
                If you didn't request this, you can safely ignore this email.
            </p>
            
            <p style="font-size: 14px; color: rgba(255, 255, 255, 0.6);">
                Or copy this link: <br>
                <a href="{reset_url}" style="color: #00d4ff;">{reset_url}</a>
            </p>
            
            <hr style="border: none; border-top: 1px solid rgba(0, 212, 255, 0.1); margin: 30px 0;">
            
            <p style="font-size: 12px; color: rgba(255, 255, 255, 0.4); text-align: center;">
                © 2025 ClervIQ - AI Receptionist Platform
            </p>
        </div>
    </body>
    </html>
    """
    
    mail.send(msg)

@password_reset_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        from app import User
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            serializer = get_serializer()
            token = serializer.dumps(email, salt='password-reset-salt')
            
            # Create reset URL
            reset_url = url_for('password_reset.reset_password', token=token, _external=True)
            
            # Send email
            try:
                send_reset_email(email, reset_url)
                flash('Password reset link sent to your email!', 'success')
            except Exception as e:
                print(f"Error sending email: {e}")
                flash('Error sending email. Please try again.', 'error')
        else:
            # Don't reveal if email exists or not (security)
            flash('If that email exists, a reset link has been sent.', 'info')
        
        return redirect(url_for('password_reset.forgot_password'))
    
    return render_template('forgot_password.html')

@password_reset_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    serializer = get_serializer()
    
    try:
        # Verify token (expires in 1 hour)
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('Reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('password_reset.forgot_password'))
    except BadSignature:
        flash('Invalid reset link.', 'error')
        return redirect(url_for('password_reset.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Update password
        from app import User, db, bcrypt
        user = User.query.filter_by(email=email).first()
        
        if user:
            user.password = bcrypt.generate_password_hash(password).decode('utf-8')
            db.session.commit()
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('User not found.', 'error')
            return redirect(url_for('password_reset.forgot_password'))
    
    return render_template('reset_password.html', token=token)