from uuid import uuid4

import pymysql
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "change-this-in-prod"

# ====== DB 접속 설정 (상수) ======
DB_HOST = "211.47.75.102"
DB_USER = "ramitakorea"
DB_PASSWORD = "finedata1230!"
DB_NAME = "dbramitakorea"


def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        use_unicode=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


@app.route("/")
def index():
    if "session_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", message="Hello, Flask!")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["session_id"] = str(uuid4())
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    signup_type = request.args.get("type")
    partner_type = request.args.get("partner_type")
    message = None
    error = None

    if request.method == "POST":
        form = request.form
        signup_type = form.get("signup_type") or signup_type
        partner_type = form.get("partner_type") or partner_type
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                if signup_type == "partner" and partner_type == "company":
                    contact_email = form.get("contact_email", "").strip()
                    contact_name = form.get("contact_name", "").strip()
                    contact_phone = form.get("contact_phone", "").strip()
                    display_name = form.get("legal_name", "").strip()

                    cursor.execute(
                        """
                        INSERT INTO users (email, name, phone)
                        VALUES (%s, %s, %s)
                        """,
                        (contact_email, contact_name or display_name, contact_phone or None),
                    )
                    user_id = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO partners (code, display_name, partner_type, contact_name, contact_email, contact_phone, country, region)
                        VALUES (%s, %s, 'company', %s, %s, %s, %s, %s)
                        """,
                        (
                            "TEMP",
                            display_name,
                            contact_name or None,
                            contact_email or None,
                            contact_phone or None,
                            form.get("country") or None,
                            form.get("region") or None,
                        ),
                    )
                    partner_id = cursor.lastrowid

                    cursor.execute(
                        "UPDATE partners SET code=%s WHERE id=%s",
                        (f"PTN-{partner_id:06d}", partner_id),
                    )

                    cursor.execute(
                        """
                        INSERT INTO partner_company_profiles
                        (partner_id, legal_name, business_registration_no, representative_name, address_line1, address_line2, tax_email)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            partner_id,
                            display_name,
                            form.get("business_registration_no") or None,
                            form.get("representative_name") or None,
                            form.get("address_line1") or None,
                            form.get("address_line2") or None,
                            form.get("tax_email") or None,
                        ),
                    )

                    cursor.execute(
                        """
                        INSERT INTO partner_memberships (partner_id, user_id, membership_role)
                        VALUES (%s, %s, 'owner')
                        """,
                        (partner_id, user_id),
                    )

                elif signup_type == "partner" and partner_type == "individual":
                    contact_email = form.get("contact_email", "").strip()
                    full_name = form.get("name", "").strip()
                    contact_phone = form.get("contact_phone", "").strip()

                    cursor.execute(
                        """
                        INSERT INTO users (email, name, phone)
                        VALUES (%s, %s, %s)
                        """,
                        (contact_email, full_name, contact_phone or None),
                    )
                    user_id = cursor.lastrowid

                    cursor.execute(
                        """
                        INSERT INTO partners (code, display_name, partner_type, contact_name, contact_email, contact_phone, country, region)
                        VALUES (%s, %s, 'individual', %s, %s, %s, %s, %s)
                        """,
                        (
                            "TEMP",
                            full_name,
                            full_name or None,
                            contact_email or None,
                            contact_phone or None,
                            form.get("country") or None,
                            form.get("region") or None,
                        ),
                    )
                    partner_id = cursor.lastrowid

                    cursor.execute(
                        "UPDATE partners SET code=%s WHERE id=%s",
                        (f"PTN-{partner_id:06d}", partner_id),
                    )

                    cursor.execute(
                        """
                        INSERT INTO partner_individual_profiles
                        (partner_id, nationality, residency_status)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            partner_id,
                            form.get("nationality") or None,
                            form.get("residency_status") or None,
                        ),
                    )

                    cursor.execute(
                        """
                        INSERT INTO partner_memberships (partner_id, user_id, membership_role)
                        VALUES (%s, %s, 'owner')
                        """,
                        (partner_id, user_id),
                    )

                elif signup_type == "staff":
                    email = form.get("email", "").strip()
                    name = form.get("name", "").strip()
                    phone = form.get("phone", "").strip()
                    role_name = form.get("role", "").strip()

                    cursor.execute(
                        """
                        INSERT INTO users (email, name, phone)
                        VALUES (%s, %s, %s)
                        """,
                        (email, name, phone or None),
                    )
                    user_id = cursor.lastrowid

                    if role_name:
                        cursor.execute(
                            "INSERT IGNORE INTO roles (name) VALUES (%s)",
                            (role_name,),
                        )
                        cursor.execute("SELECT id FROM roles WHERE name=%s", (role_name,))
                        role = cursor.fetchone()
                        if role:
                            cursor.execute(
                                """
                                INSERT INTO user_roles (user_id, role_id)
                                VALUES (%s, %s)
                                """,
                                (user_id, role["id"]),
                            )
                else:
                    error = "Invalid signup type."

            if error is None:
                conn.commit()
                message = "가입 신청이 완료되었습니다."
        except Exception as exc:
            if conn:
                conn.rollback()
            error = f"가입 처리 중 오류가 발생했습니다: {exc}"
        finally:
            if conn:
                conn.close()

    return render_template(
        "signup.html",
        signup_type=signup_type,
        partner_type=partner_type,
        message=message,
        error=error,
    )


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True)
