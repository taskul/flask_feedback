from flask import Flask, render_template, flash, redirect, session
from models import connect_db, db, User, Feedback
from forms import CreateUser, LoginUser, FeedbackForm
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Unauthorized

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///flask_feedback.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False

connect_db(app)
app.app_context().push()


@app.route("/")
def home():
    return redirect("/register")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(f'/users/{session["user_id"]}')
    form = CreateUser()
    if form.validate_on_submit():
        new_user = User.register(
            username=form.username.data,
            password=form.password.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
        )
        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            form.username.errors.append("Username taken.  Please pick another")
            return render_template("register.html", form=form)
        flash("Welcome! Successfully Created Your Account!", "success")
        session["user_id"] = new_user.username
        return redirect(f"/users/{new_user.username}")
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login_user():
    if "user_id" in session:
        return redirect(f'/users/{session["user_id"]}')
    form = LoginUser()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.authenticate(username, password)
        if user:
            session["user_id"] = user.username
            flash(f"Welcome back {user.username}!")
            return redirect(f"/users/{user.username}")
        else:
            form.username.errors = ["Invalid username/password."]
            return render_template("login.html", form=form)
    return render_template("login.html", form=form)


# logging out should be a POST request to avoid external sites from logging us out
@app.route("/logout")
def logout_user():
    session.pop("user_id")
    flash("You have been logged out.", "info")
    return redirect("/")


@app.route("/users/<username>")
def user_page(username):
    if "user_id" not in session or username != session["user_id"]:
        raise Unauthorized()
    user = User.query.get_or_404(username)
    return render_template("user_page.html", user=user)


@app.route("/users/<username>/delete", methods=["POST"])
def delete_user(username):
    if "user_id" not in session or username != session["user_id"]:
        raise Unauthorized()
    if username == session["user_id"]:
        user = User.query.get(username)
        db.session.delete(user)
        db.session.commit()
        session.pop("user_id")
    return redirect("/")


# ----------------------------------------Feedback Routes ------------------------------
@app.route("/users/<username>/feedback/add", methods=["GET", "POST"])
def add_feedback(username):
    if "user_id" not in session:
        flash("You need to login to access this content")
        return redirect("/login")
    form = FeedbackForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        new_feedback = Feedback(title=title, content=content, username=username)
        db.session.add(new_feedback)
        db.session.commit()
        flash("Your feedback has been recorded", "success")
        return redirect(f"/users/{username}")
    return render_template("add_feedback.html", form=form)


@app.route("/feedback/<int:feedback_id>/update", methods=["GET", "POST"])
def update_feedback(feedback_id):
    feedback = Feedback.query.get(feedback_id)
    if "user_id" not in session or feedback.username != session["user_id"]:
        raise Unauthorized()

    feedback = Feedback.query.get(feedback_id)
    form = FeedbackForm(obj=feedback)
    if form.validate_on_submit():
        feedback.title = form.title.data
        feedback.content = form.content.data
        db.session.commit()
        flash("Your feedback has been updated", "success")
        return redirect(f"/users/{feedback.username}")
    return render_template("add_feedback.html", form=form)


@app.route("/feedback/<int:feedback_id>/delete", methods=["POST"])
def delete_feedback(feedback_id):
    feedback = Feedback.query.get(feedback_id)
    if "user_id" not in session or feedback.username != session["user_id"]:
        raise Unauthorized()
    db.session.delete(feedback)
    db.session.commit()
    return redirect(f"/users/{feedback.username}")


if __name__ == "__main__":
    app.run(debug=True)
