"""GR Asset Management System — app factory"""
from flask import Flask
from extensions import db, login_manager
from datetime import datetime
import os


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # ── Load .env file if it exists ──────────────────────────────
    _load_env(os.path.join(os.path.dirname(__file__), '.env'))

    app.config['SECRET_KEY'] = 'gr-ams-secret-key-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'sqlite:///' + os.path.join(app.instance_path, 'gr_ams.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    os.makedirs(app.instance_path, exist_ok=True)

    # ── Mail config (loaded from .env) ───────────────────────────
    app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER',   'smtp.office365.com')
    app.config['MAIL_PORT']     = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['APP_URL']       = os.environ.get('APP_URL',       'http://127.0.0.1:5000')
    app.config['MAIL_USE_SSL']  = os.environ.get('MAIL_USE_SSL',  'false')
    app.config['ORG_NAME']      = os.environ.get('ORG_NAME',      'GR')

    db.init_app(app)
    login_manager.init_app(app)

    from routes.auth     import auth_bp
    from routes.main     import main_bp
    from routes.assets   import assets_bp
    from routes.users    import users_bp
    from routes.admin    import admin_bp
    from routes.reports  import reports_bp
    from routes.requests import requests_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(assets_bp,   url_prefix='/assets')
    app.register_blueprint(users_bp,    url_prefix='/users')
    app.register_blueprint(admin_bp,    url_prefix='/admin')
    app.register_blueprint(reports_bp,  url_prefix='/reports')
    app.register_blueprint(requests_bp, url_prefix='/requests')

    @app.template_filter('currency')
    def currency_filter(v):
        try:    return 'UGX {:,.0f}'.format(float(v or 0))
        except: return 'UGX 0'

    @app.template_filter('dateformat')
    def date_filter(v):
        if not v: return '—'
        if isinstance(v, str):
            try: v = datetime.strptime(v, '%Y-%m-%d')
            except: return v
        return v.strftime('%d %b %Y')

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        counts = {'pending_asset_requests': 0, 'pending_return_requests': 0}
        try:
            if current_user.is_authenticated and current_user.role in ('admin', 'finance'):
                from models import AssetRequest, ReturnRequest
                counts['pending_asset_requests']  = AssetRequest.query.filter_by(status='pending').count()
                counts['pending_return_requests'] = ReturnRequest.query.filter_by(status='pending').count()
        except Exception:
            pass
        counts['now'] = datetime.utcnow()
        return counts

    with app.app_context():
        db.create_all()
        # Ensure new columns added when model changed (simple SQLite-friendly migration)
        try:
            from sqlalchemy import text
            cols = [r['name'] for r in db.session.execute(text("PRAGMA table_info('assets')")).mappings()]
        except Exception:
            cols = []
        alter_stmts = []
        if 'processor' not in cols:
            alter_stmts.append("ALTER TABLE assets ADD COLUMN processor TEXT")
        if 'age_years' not in cols:
            alter_stmts.append("ALTER TABLE assets ADD COLUMN age_years INTEGER")
        if 'age_months' not in cols:
            alter_stmts.append("ALTER TABLE assets ADD COLUMN age_months INTEGER")
        for s in alter_stmts:
            try:
                db.session.execute(text(s))
            except Exception:
                pass
        if alter_stmts:
            db.session.commit()

        _seed()

    return app


def _seed():
    from models import User, AssetCategory, Project, Vendor, Asset, Role
    from werkzeug.security import generate_password_hash
    if not Role.query.first():
        roles = [
            Role(name='admin', label='Administrator', description='Full system administrator access.'),
            Role(name='finance', label='Finance Officer', description='Finance team access and reporting approvals.'),
            Role(name='user', label='Staff User', description='Standard staff access to own assets and requests.'),
        ]
        db.session.add_all(roles)
        db.session.flush()
    if User.query.first():
        return
    print("  Seeding database ...")
    users = [
        User(username='admin',   name='System Administrator', email='admin@gr.org',
             role='admin',   department='IT',       status='active',
             password_hash=generate_password_hash('admin123')),
        User(username='finance', name='Sarah Nakato',          email='sarah@gr.org',
             role='finance', department='Finance',  status='active',
             password_hash=generate_password_hash('finance123')),
        User(username='john',    name='John Okello',           email='john@gr.org',
             role='user',    department='Programs', status='active',
             password_hash=generate_password_hash('user123')),
        User(username='mary',    name='Mary Apio',             email='mary@gr.org',
             role='user',    department='Admin',    status='active',
             password_hash=generate_password_hash('user123')),
    ]
    db.session.add_all(users); db.session.flush()

    cats = [
        AssetCategory(name='Laptop',    code='LP',   description='Laptop computers'),
        AssetCategory(name='Desktop',   code='DISC', description='Desktop computers'),
        AssetCategory(name='Printer',   code='PRN',  description='Printers and scanners'),
        AssetCategory(name='Furniture', code='FRN',  description='Office furniture'),
        AssetCategory(name='Vehicle',   code='VEH',  description='Vehicles'),
        AssetCategory(name='UPS',       code='UPS',  description='Uninterruptible power supply'),
        AssetCategory(name='Projector', code='PROJ', description='Projectors'),
        AssetCategory(name='Phone',     code='PHN',  description='Mobile phones'),
    ]
    db.session.add_all(cats); db.session.flush()

    projs = [
        Project(code='CORE', name='Core Operations',   description='Main operational budget',   status='active', year='2024'),
        Project(code='HLTH', name='Health Initiative',  description='Community health programs', status='active', year='2024'),
        Project(code='EDU',  name='Education Program',  description='Schools and training',      status='active', year='2024'),
    ]
    db.session.add_all(projs); db.session.flush()

    vendors = [
        Vendor(name='TechHub Uganda',       contact='+256 700 111 222', email='info@techhub.ug', address='Kampala'),
        Vendor(name='Computer Palace',      contact='+256 700 333 444', email='info@cpalace.ug', address='Kampala'),
        Vendor(name='Office Solutions Ltd', contact='+256 700 555 666', email='info@osl.ug',     address='Jinja'),
    ]
    db.session.add_all(vendors); db.session.flush()

    from datetime import date
    lp,disc,prn  = cats[0],cats[1],cats[2]
    core,hlth,edu= projs[0],projs[1],projs[2]
    v1,v2,v3     = vendors[0],vendors[1],vendors[2]
    john,sarah,mary = users[2],users[1],users[3]
    def t(p,c,n): return f"GR-{c.code}-{p.code}-{n:03d}"

    assets = [
        Asset(asset_number=1,tag=t(core,lp,1),serial_number='SN-DELL-001',name='Dell Latitude 5420',
              category=lp,project=core,vendor=v1,price=1800000,date_purchased=date(2024,1,15),
              condition='good',status='active',assigned_to_id=john.id,assigned_on=date(2024,1,20),
              description='Intel Core i5, 8GB RAM, 256GB SSD',location='Kampala Office'),
        Asset(asset_number=2,tag=t(core,lp,2),serial_number='SN-HP-002',name='HP ProBook 450',
              category=lp,project=core,vendor=v2,price=1500000,date_purchased=date(2024,1,20),
              condition='good',status='active',assigned_to_id=sarah.id,assigned_on=date(2024,1,25),
              description='Intel Core i5, 8GB RAM',location='Kampala Office'),
        Asset(asset_number=3,tag=t(hlth,disc,1),serial_number='SN-DESK-003',name='HP Desktop ProDesk',
              category=disc,project=hlth,vendor=v1,price=1200000,date_purchased=date(2024,2,10),
              condition='good',status='active',assigned_to_id=mary.id,assigned_on=date(2024,2,15),
              description='Core i5, 16GB RAM, 1TB HDD',location='Jinja Office'),
        Asset(asset_number=4,tag=t(edu,prn,1),serial_number='SN-PRN-004',name='HP LaserJet Pro',
              category=prn,project=edu,vendor=v3,price=850000,date_purchased=date(2024,2,20),
              condition='fair',status='active',description='A4 laser printer',location='Training Center'),
        Asset(asset_number=5,tag=t(core,lp,3),serial_number='SN-LENOVO-005',name='Lenovo ThinkPad L14',
              category=lp,project=core,vendor=v1,price=1950000,date_purchased=date(2024,3,5),
              condition='new',status='active',description='AMD Ryzen 5, 16GB RAM, 512GB SSD',location='Kampala Office'),
    ]
    db.session.add_all(assets)
    db.session.commit()
    print("  Database seeded OK.")


def _load_env(path):
    """Simple .env loader — no dependencies needed."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
