import os
import datetime
import tempfile
import smtplib
import boto3

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def get_first_and_last_name():
    MY_FULL_NAME = str(os.environ["PERSON_NAME"])

    if len(MY_FULL_NAME.split(" ")) > 1:
        splitted_name = MY_FULL_NAME.split(" ")
        first_name = splitted_name[0]
        last_name = splitted_name[-1]
        return first_name, last_name
    elif MY_FULL_NAME:
        return MY_FULL_NAME, ""


def get_current_month_info():
    now = datetime.datetime.now()
    first_day = datetime.datetime(now.year, now.month, 1)
    next_month = first_day.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)
    return {
        "year": now.year,
        "month_name": now.strftime("%B"),
        "first_day": first_day,
        "last_day": last_day,
    }


def build_invoice_pdf(pdf_path: str, month_info: dict):
    
    MY_PROFESSION       = os.environ["INVOICE_SERVICE_DESCRIPTION"]
    CURRENCY_TO_BE_PAID = os.environ["INVOICE_CURRENCY"]
    AMOUNT              = int(os.environ["INVOICE_AMOUNT"])

    MY_FULL_NAME        = os.environ["PERSON_NAME"]
    MY_NIF              = os.environ["PERSON_TAX_ID"]
    MY_ADDRESS          = os.environ["PERSON_ADDRESS"]
    MY_POSTCODE         = os.environ["PERSON_POSTCODE"]
    MY_LOCATION         = os.environ["PERSON_CITY"]
    MY_COUNTRY          = os.environ["PERSON_COUNTRY"]
    MY_PHONE            = os.environ["PERSON_PHONE"]
    MY_HOTMAIL          = os.environ["EMAIL_CC_ADDRESS"]

    MY_IBAN             = os.environ["BANK_IBAN"]
    MY_SWIFT            = os.environ["BANK_SWIFT"]
    MY_CORR_BIC         = os.environ["BANK_CORRESPONDENT_BIC"]

    EMPLOYER_NAME       = os.environ["CLIENT_NAME"]
    EMPLOYER_ADDRESS    = os.environ["CLIENT_ADDRESS"]
    EMPLOYER_TAXID      = os.environ["CLIENT_TAX_ID"]

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    elements = []

    styles       = getSampleStyleSheet()
    title_style  = ParagraphStyle(name="Title",  fontSize=18, leading=24,
                                  alignment=1, spaceAfter=10)
    normal_style = ParagraphStyle(name="Normal", parent=styles["Normal"],
                                  fontSize=11, leading=16)

    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Paragraph(
        f"<b>{month_info['month_name']} {month_info['year']}</b>", normal_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 16))

    # Sender (issuer) info
    elements.append(Paragraph(f"""
<b>Name:</b> {MY_FULL_NAME}<br/>
<b>Tax ID:</b> {MY_NIF}<br/>
<b>Address:</b> {MY_ADDRESS}<br/>
<b>Postal Code:</b> {MY_POSTCODE}<br/>
<b>Location:</b> {MY_LOCATION}<br/>
<b>Country:</b> {MY_COUNTRY}<br/>
<b>Phone:</b> {MY_PHONE}<br/>
<b>Email:</b> {MY_HOTMAIL}
""", normal_style))
    elements.append(Spacer(1, 10))

    # Client info
    elements.append(Paragraph(f"""
<b>To: {EMPLOYER_NAME}</b><br/>
<b>Address:</b> {EMPLOYER_ADDRESS}<br/>
<b>Tax ID:</b> {EMPLOYER_TAXID}
""", normal_style))
    elements.append(Spacer(1, 18))

    # Period
    elements.append(Paragraph(
        f"<b>Invoice period:</b> "
        f"{month_info['first_day'].strftime('%d %B %Y')} – "
        f"{month_info['last_day'].strftime('%d %B %Y')}",
        normal_style
    ))
    elements.append(Spacer(1, 12))

    # Table
    generated_date = month_info["last_day"].strftime("%d %B %Y")
    due_date       = (month_info["last_day"] + datetime.timedelta(days=10)
                      ).strftime("%d %B %Y")

    invoice_data = [
        ["Service", "Document Date", "Due Date", "Currency", "Total Amount"],
        [MY_PROFESSION,
         generated_date, due_date, CURRENCY_TO_BE_PAID, f"{AMOUNT:.2f}"]
    ]

    table = Table(invoice_data,
                  colWidths=[150, 100, 100, 60, 100], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID",        (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND",  (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("TOPPADDING",    (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (1, 1), (-1, -1), 8),
        ("TOPPADDING",    (1, 1), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 18))

    # Bank transfer info
    elements.append(Paragraph(f"""
<b><i>Information for Bank Transfer:</i></b><br/><br/>
<b>IBAN:</b> {MY_IBAN}<br/>
<b>SWIFT/BIC:</b> {MY_SWIFT}<br/>
<b>Correspondent BIC:</b> {MY_CORR_BIC}
""", normal_style))

    doc.build(elements)

    return pdf_path


def send_email(pdf_path: str, month_info: dict):
    sender      = os.environ["EMAIL_SENDER_ADDRESS"]
    to_addr     = os.environ["EMAIL_RECIPIENT_ADDRESS"]
    cc_addr     = os.environ["EMAIL_CC_ADDRESS"]
    password    = os.environ["EMAIL_SENDER_PASSWORD"]

    email_body_send_to_name = os.environ["EMAIL_GREETING_NAME"]
    email_body_my_name      = os.environ["EMAIL_SIGNATURE_NAME"]

    first_name, last_name = get_first_and_last_name()

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"]   = to_addr
    msg["Cc"]   = cc_addr
    msg["Subject"] = (
        f"{first_name} {last_name} – Invoice for {month_info['month_name']} {month_info['year']}"
    )

    msg.attach(MIMEText(
        f"""Hi {email_body_send_to_name},

Please find attached the invoice for {month_info['month_name']} {month_info['year']}.

Best regards,
{email_body_my_name}""",
        "plain"
    ))

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header("Content-Disposition", "attachment",
                        filename=os.path.basename(pdf_path))
        msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)

    print("Invoice email sent successfully")


def optionally_upload_to_s3(pdf_path: str):
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        return

    key = os.path.basename(pdf_path)
    boto3.client("s3").upload_file(pdf_path, bucket, key)
    print(f"Saved a copy to s3://{bucket}/{key}")


#  Lambda entry point
def handler(event, context):
    month_info = get_current_month_info()

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_name = (f"DuartePombo_{month_info['month_name']}_"
                    f"{month_info['year']}_invoice.pdf")
        pdf_path = os.path.join(tmpdir, pdf_name)

        build_invoice_pdf(pdf_path, month_info)
        send_email(pdf_path, month_info)
        optionally_upload_to_s3(pdf_path)

    return {"status": "ok", "month": month_info["month_name"],
            "year": month_info["year"]}
