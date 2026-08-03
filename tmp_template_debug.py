from app import create_app
from types import SimpleNamespace
import traceback

app = create_app()
with app.app_context():
    user = SimpleNamespace(is_staff_portal=False, role='admin')
    projects = []
    assets = []
    try:
        t = app.jinja_env.get_template('assets/index.html')
        print('template loaded')
        output = t.render(q='', proj_id=None, cond='', assets=assets, projects=projects, current_user=user)
        print('render success')
        print(output[:500])
    except Exception:
        traceback.print_exc()
