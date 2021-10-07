from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

from werkzeug.utils import secure_filename

from datetime import datetime
import json
import os
import math

with open('config.json', 'r') as config_file:
    params = json.load(config_file)['params']

LOCAL_SERVER = params['local_server']
SERVER_URI = None
EMAIL_ADDRESS = params['email-address']
EMAIL_PASSWORD = params['email-password']

if LOCAL_SERVER:
    SERVER_URI = params['local_uri']
else:
    SERVER_URI = params['production_uri']

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = SERVER_URI
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=EMAIL_ADDRESS,
    MAIL_PASSWORD=EMAIL_PASSWORD
)

app.secret_key = '9io-*lb#5HIxQSS-A!meJN8B$-d$!LZbx*f3L0jg'

db = SQLAlchemy(app)
mail = Mail(app)


class ContactMessages(db.Model):
    s_no = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(60), nullable=False)
    phone_no = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20), nullable=False)


class Posts(db.Model):
    s_no = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    thumb_img_url = db.Column(db.String(50), nullable=True)
    date = db.Column(db.String(20), nullable=True)


@app.route('/')
def index():
    home_post_limit = params['posts-limit-home']

    posts = Posts.query.filter_by().all()

    last_page_no = math.ceil(len(posts) / home_post_limit)
    cur_page_no = request.args.get('page-no')

    if cur_page_no is None:
        cur_page_no = 1
    cur_page_no = int(cur_page_no)

    if cur_page_no == 1:
        prev_page = None
        next_page = f'/?page-no={cur_page_no + 1}'

    elif cur_page_no == last_page_no:
        prev_page = f'/?page-no={cur_page_no - 1}'
        next_page = None

    else:
        prev_page = f'/?page-no={cur_page_no - 1}'
        next_page = f'/?page-no={cur_page_no + 1}'

    posts = Posts.query.paginate(cur_page_no, home_post_limit, error_out=False).items

    return render_template('index.html', params=params, posts=posts, prev_page=prev_page, next_page=next_page)


@app.route('/about')
def about():
    return render_template('about.html', params=params)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        """ Add the Entry to the Database """

        name = request.form.get('name')
        email = request.form.get('email')
        phone_no = request.form.get('phone_no')
        msg = request.form.get('msg')
        date = datetime.now()

        entry = ContactMessages(name=name, email=email, phone_no=phone_no, msg=msg, date=date)

        db.session.add(entry)
        db.session.commit()

        mail.send_message(
            f"'New Message from {params['app_name']}' by {name}",
            sender=email,
            recipients=[EMAIL_ADDRESS],
            body=f"Phone Number: {phone_no}\n\n{msg}"
        )

    return render_template('contact.html', params=params)


@app.route('/posts/<string:post_slug>', methods=['GET'])
def post(post_slug):
    post_ = Posts.query.filter_by(slug=post_slug).first()

    return render_template('post.html', params=params, post=post_)


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_username' in session and session['admin_username'] == params['admin_username']:
        return redirect('/admin-panel')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == params['admin_username'] and password == params['admin_password']:
            session['admin_username'] = username

            return redirect('/admin-panel')

    else:
        return render_template('admin_login.html', params=params)


@app.route('/admin-panel')
def admin_panel():
    if not ('admin_username' in session and session['admin_username'] == params['admin_username']):
        return redirect('/admin-login')

    posts = Posts.query.all()

    return render_template('admin_panel.html', params=params, posts=posts)


@app.route('/admin-panel/posts/add-edit/<string:s_no>', methods=['GET', 'POST'])
def edit_post(s_no):
    if not ('admin_username' in session and session['admin_username'] == params['admin_username']):
        return redirect('/admin-login')

    if request.method == 'POST':
        title = request.form.get('title')
        sub_title = request.form.get('sub_title')
        slug = request.form.get('slug')
        content = request.form.get('content')
        thumb_img = request.files['thumb-img']
        date = datetime.now()

        thumb_img_path = os.path.join(
            os.path.join(os.getcwd(), params['thumb-img-location']),
            secure_filename(thumb_img.filename)
        )

        print(thumb_img_path)
        thumb_img.save(thumb_img_path)

        if s_no == '0':
            post_ = Posts(
                title=title,
                subtitle=sub_title,
                slug=slug,
                content=content,
                date=date,
                thumb_img_url=secure_filename(thumb_img.filename)
            )

            db.session.add(post_)
            db.session.commit()

        else:
            post_ = Posts.query.filter_by(s_no=s_no).first()

            post_.title = title
            post_.subtitle = sub_title
            post_.slug = slug
            post_.content = content
            post_.date = date
            post_.thumb_img_url = secure_filename(thumb_img.filename)

            db.session.commit()

        return redirect('/admin-panel')

    post_ = Posts.query.filter_by(s_no=s_no).first()

    return render_template('edit_post.html', params=params, post_s_no=s_no, post=post_)


@app.route('/admin-panel/posts/delete/<string:s_no>', methods=['GET', 'POST'])
def delete_post(s_no):
    if not ('admin_username' in session and session['admin_username'] == params['admin_username']):
        return redirect('/admin-login')

    post_ = Posts.query.filter_by(s_no=s_no).first()

    db.session.delete(post_)
    db.session.commit()

    return redirect('/admin-panel')


@app.route('/admin-panel/logout')
def logout():
    session.pop('admin_username')

    return redirect('/admin-panel')


if __name__ == '__main__':
    app.run(debug=True)
