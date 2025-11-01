"""
Calendar OAuth and management routes
"""
from flask import Blueprint, request, redirect, render_template_string
from ..models.database import db, User
from ..services.calendar_service import CalendarService

bp = Blueprint('calendar', __name__, url_prefix='/calendar')
calendar_service = CalendarService()

@bp.route('/connect/<int:user_id>')
def connect_calendar(user_id):
    """Generate OAuth URL and redirect user"""
    try:
        user = User.query.get(user_id)
        if not user:
            return render_template_string("""
                <html dir="rtl">
                <head><meta charset="utf-8"><title>שגיאה</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ שגיאה</h1>
                    <p>משתמש לא נמצא.</p>
                </body>
                </html>
            """), 404
        
        auth_url = calendar_service.get_authorization_url(user_id)
        return redirect(auth_url)
        
    except ValueError as e:
        return render_template_string("""
            <html dir="rtl">
            <head><meta charset="utf-8"><title>שגיאה</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ שגיאה בהגדרה</h1>
                <p>{{ error }}</p>
                <p>אנא פנה לתמיכה.</p>
            </body>
            </html>
        """, error=str(e)), 500
        
    except Exception as e:
        print(f"❌ Error generating auth URL: {e}")
        return render_template_string("""
            <html dir="rtl">
            <head><meta charset="utf-8"><title>שגיאה</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ שגיאה</h1>
                <p>שגיאה ביצירת קישור החיבור. נסה שוב מאוחר יותר.</p>
            </body>
            </html>
        """), 500

@bp.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth callback from Google"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')  # Contains user_id
        error = request.args.get('error')
        
        if error:
            return render_template_string("""
                <html dir="rtl">
                <head><meta charset="utf-8"><title>שגיאה</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ שגיאה בחיבור ליומן</h1>
                    <p>{{ error }}</p>
                    <p>אתה יכול לסגור חלון זה ולנסות שוב.</p>
                </body>
                </html>
            """, error=error)
        
        if not code or not state:
            return render_template_string("""
                <html dir="rtl">
                <head><meta charset="utf-8"><title>שגיאה</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ שגיאה</h1>
                    <p>פרמטרים חסרים בהרשאה. נסה להתחבר מחדש.</p>
                </body>
                </html>
            """), 400
        
        try:
            user_id = int(state)
        except ValueError:
            return render_template_string("""
                <html dir="rtl">
                <head><meta charset="utf-8"><title>שגיאה</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ שגיאה</h1>
                    <p>מזהה משתמש לא תקין.</p>
                </body>
                </html>
            """), 400
        
        success, message = calendar_service.handle_oauth_callback(code, user_id)
        
        if success:
            return render_template_string("""
                <html dir="rtl">
                <head><meta charset="utf-8"><title>הצלחה!</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>✅ היומן חובר בהצלחה!</h1>
                    <p>עכשיו כל משימה עם תאריך יעד תתווסף אוטומטית ליומן Google שלך.</p>
                    <p><strong>אתה יכול לסגור חלון זה ולחזור לWhatsApp</strong></p>
                    <hr>
                    <p style="color: gray; font-size: 12px;">TodoBot - מנהל המשימות החכם שלך</p>
                </body>
                </html>
            """)
        else:
            return render_template_string("""
                <html dir="rtl">
                <head><meta charset="utf-8"><title>שגיאה</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ שגיאה</h1>
                    <p>{{ message }}</p>
                    <p>אנא נסה שוב או פנה לתמיכה.</p>
                </body>
                </html>
            """, message=message)
        
    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        return render_template_string("""
            <html dir="rtl">
            <head><meta charset="utf-8"><title>שגיאה</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>❌ שגיאה</h1>
                <p>שגיאה בעיבוד ההרשאה. אנא נסה שוב.</p>
            </body>
            </html>
        """), 500

@bp.route('/disconnect/<int:user_id>', methods=['POST'])
def disconnect_calendar(user_id):
    """Disconnect user's calendar"""
    try:
        success, message = calendar_service.disconnect_calendar(user_id)
        return {"success": success, "message": message}, 200 if success else 500
    except Exception as e:
        return {"success": False, "message": str(e)}, 500

@bp.route('/status/<int:user_id>')
def calendar_status(user_id):
    """Check calendar connection status"""
    try:
        user = User.query.get(user_id)
        if not user:
            return {"connected": False, "message": "User not found"}, 404
        
        return {
            "connected": user.google_calendar_enabled,
            "calendar_id": user.google_calendar_id if user.google_calendar_enabled else None
        }
    except Exception as e:
        return {"error": str(e)}, 500

