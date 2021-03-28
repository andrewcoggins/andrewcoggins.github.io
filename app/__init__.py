from flask import current_app, flash, Flask, Markup, render_template, request, session, url_for
from datetime import datetime


def create_app(package_assets=False):
    app = Flask(__name__)

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True
    app.jinja_env.globals["now"] = datetime.now
    app.jinja_env.globals["try_url_for"] = try_url_for

    if app.debug and not package_assets:
        print("{}\n>>> App Configured for: Development\n{}".format("*" * 40, "*" * 40))
        app.config["ASSETS_DEBUG"] = True
        app.config["FLASKS3_ACTIVE"] = False
        app.config["FLASKS3_DEBUG"] = True
        app.config["USAGE_DEBUG"] = True

    else:
        print("{}\n>>> App Configured for: Production\n{}".format("*" * 40, "*" * 40))
        app.config["FLASK_ASSETS_USE_S3"] = True


    # configure app via environment (will overwrite debug to FALSE)
    bapconfig.init_app(app)

    # setup SQLAlchemy URI (fetch password from SSM Parameter Store)
    setup_sqlalchemy_uri(app)
    db.init_app(app)

    # remainder of instantiation
    assets.init_app(app)
    bootstrap.init_app(app)
    s3.init_app(app)
    ses.init_app(app)

    app.logger.setLevel(logging.INFO)

    loader = YAMLLoader("assets.yaml")
    assets.register(loader.load_bundles())

    from . import main, auth, batchkins, commercial, customer, drug, formulary, kdm, medicaid, medicare, policy, \
        system, tax, xref

    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp, url_prefix="/auth")
    app.register_blueprint(batchkins.bp, url_prefix="/batchkins")
    app.register_blueprint(commercial.bp, url_prefix="/commercial")
    app.register_blueprint(customer.bp, url_prefix="/customer")
    app.register_blueprint(drug.bp, url_prefix="/drug")
    app.register_blueprint(formulary.bp, url_prefix="/formulary")
    app.register_blueprint(kdm.bp, url_prefix="/kdm")
    app.register_blueprint(medicaid.bp, url_prefix="/medicaid")
    app.register_blueprint(medicare.bp, url_prefix="/medicare")
    app.register_blueprint(policy.bp, url_prefix="/policy")
    app.register_blueprint(system.bp, url_prefix="/system")
    app.register_blueprint(tax.bp, url_prefix="/tax")
    app.register_blueprint(xref.bp, url_prefix="/xref")

    @app.before_request
    def before_request():
        aws_auth.check_credentials()

        if not request.headers.get("X-Requested-With") == "XMLHttpRequest" and request.endpoint != "static":
            """ Alert Users of < IE11 """
            if request.user_agent.browser == "msie" and int(request.user_agent.version.split(".")[0]) < 11:
                link = "https://www.microsoft.com/en-us/WindowsForBusiness/End-of-IE-support"
                flash(Markup('We\'ve detected an unsupported browser. Please upgrade to enjoy all of the modern '
                             'features of our application.<br /><a href="{0}">{0}</a>'.format(link)))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("error/404.html", err=e), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("error/500.html", err=e), 500

    @app.context_processor
    def inject_context():
        modules = []

        try:
            if "user" in session and len(session["access"]):

                from .system.models import Module, Usage
                email = session["user"]["email"]
                stats = {z.module: {"t": z.total, "f": z.favorite, "r": z.recent}
                         for z in Usage.query.filter_by(email=email)}

                def get_val(l, key, match):
                    out = next((i for i, v in enumerate(l) if v[key] == match), len(l))
                    if out == len(l):
                        l.append({key: match, "order": out + 1, "sub": []})
                    return out

                mods = Module.query.order_by(Module.cat_order, Module.order).filter_by(enabled=1)

                from .entitlements import has_access
                for row in mods:
                    if row.endpoint and not has_access(row.endpoint.replace(".", ":")):
                        continue

                    x, tot, fav, last = row.id, 0, 0, 0
                    cat = get_val(modules, "category", row.cat)
                    if x in stats:
                        tot, fav, last = stats[x]["t"], stats[x]["f"], mktime(stats[x]["r"].timetuple()) * 1000
                    modules[cat]["sub"].append({"id": x, "name": row.name, "desc": row.description, "order": row.order,
                                                "endpoint": row.endpoint, "used": tot, "fav": fav, "last": last})

                # filters out "separator only" categories...
                modules = [z for z in modules if len("".join(y["endpoint"] for y in z["sub"]))]

                # removes first/last/duplicate separators
                for x in range(len(modules)):
                    modules[x]["sub"] = clean_nav_list(modules[x]["sub"])

        except (NameError, KeyError, Exception) as err:
            print(format_exception(err))
            pass

        return {"admin_modules": modules}

    @app.route("/healthcheck")
    def healthcheck():
        return request.remote_addr, 200

    return app
