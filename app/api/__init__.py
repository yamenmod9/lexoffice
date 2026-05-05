from app.api.ai import bp as ai_bp
from app.api.appointments import bp as appointments_bp
from app.api.auth import bp as auth_bp
from app.api.cases import bp as cases_bp
from app.api.clients import bp as clients_bp
from app.api.dashboard import bp as dashboard_bp
from app.api.documents import bp as documents_bp
from app.api.enforcement import bp as enforcement_bp
from app.api.financial import bp as financial_bp
from app.api.judgments import bp as judgments_bp
from app.api.meta import bp as meta_bp
from app.api.notifications import bp as notifications_bp
from app.api.office import bp as office_bp
from app.api.onboarding import bp as onboarding_bp
from app.api.poa import bp as poa_bp
from app.api.reports import bp as reports_bp
from app.api.sessions import bp as sessions_bp
from app.api.tasks import bp as tasks_bp
from app.api.templates import bp as templates_bp
from app.api.users import bp as users_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(office_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(judgments_bp)
    app.register_blueprint(enforcement_bp)
    app.register_blueprint(poa_bp)
    app.register_blueprint(financial_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(meta_bp)
