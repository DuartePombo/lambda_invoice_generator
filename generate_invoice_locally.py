import os
import datetime
import tempfile
import smtplib
import requests

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
    MY_FULL_NAME     = str(os.environ["MY_FULL_NAME"])

    if len(MY_FULL_NAME.split(" "))>1:
        splitted_name = MY_FULL_NAME.split(" ")
        first_name = splitted_name[0]
        last_name = splitted_name[-1]
        return first_name, last_name

    elif MY_FULL_NAME:
        return MY_FULL_NAME, ""
    



def get_current_month_info():
    """
    Return a dict with year, month name, first/last day datetime objects.
    """
    now = datetime.datetime.now()
    first_day = datetime.datetime(now.year, now.month, 1)
    # Add 1 month, subtract 1 day → last day of current month
    next_month = first_day.replace(day=28) + datetime.timedelta(days=4)
    last_day = next_month - datetime.timedelta(days=next_month.day)
    return {
        "year": now.year,
        "month_name": now.strftime("%B"),
        "first_day": first_day,
        "last_day": last_day,
    }


def build_invoice_pdf(pdf_path: str, month_info: dict):
    """
    Generate the invoice PDF at 'pdf_path' using ReportLab.
    """
    MY_PROFESSION = os.environ["MY_PROFESSION"]
    CURRENCY_TO_BE_PAID = os.environ["CURRENCY_TO_BE_PAID"]
    AMOUNT           = int(os.environ["SALARY"])

    MY_FULL_NAME     = os.environ["MY_FULL_NAME"]
    MY_NIF           = os.environ["MY_NIF"]
    MY_ADDRESS       = os.environ["MY_ADDRESS"]
    MY_POSTCODE      = os.environ["MY_POSTCODE"]
    MY_LOCATION      = os.environ["MY_LOCATION"]
    MY_COUNTRY       = os.environ["MY_COUNTRY"]
    MY_PHONE         = os.environ["MY_PHONE"]
    MY_HOTMAIL       = os.environ["MY_PERSONAL_HOTMAIL"]
    MY_IBAN          = os.environ["MY_IBAN"]
    MY_SWIFT         = os.environ["MY_SWIFT"]
    MY_CORR_BIC      = os.environ["MY_CORRESPONDENT_BIC"]

    EMPLOYER_NAME    = os.environ["EMPLOYER_NAME"]
    EMPLOYER_ADDRESS = os.environ["EMPLOYER_ADDRESS"]
    EMPLOYER_TAXID   = os.environ["EMPLOYER_TAXID"]



    # ---- PDF document ----
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    elements = []

    # Styles
    styles       = getSampleStyleSheet()
    title_style  = ParagraphStyle(name="Title",  fontSize=18, leading=24,
                                  alignment=1, spaceAfter=10)
    normal_style = ParagraphStyle(name="Normal", parent=styles["Normal"],
                                  fontSize=11, leading=16)

    # Title
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Paragraph(
        f"<b>{month_info['month_name']} {month_info['year']}</b>", normal_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 16))

    # Your info
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

    # Employer info
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

    # Build
    doc.build(elements)

    return pdf_path


def send_email(pdf_path: str, month_info: dict):
    """
    Email the PDF through Gmail SMTP.
    """
    sender                  = os.environ["MY_PERSONAL_GMAIL"]
    to_addr                 = os.environ["MY_WORK_EMAIL"]
    cc_addr                 = os.environ["MY_PERSONAL_HOTMAIL"]
    password                = os.environ["EMAIL_PASSWORD"]

    email_body_send_to_name = os.environ["EMAIL_BODY_SEND_TO_NAME"]
    email_body_my_name      = os.environ["EMAIL_BODY_MY_NAME"]

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



def main():

    month_info = get_current_month_info()

    with tempfile.TemporaryDirectory() as tmpdir:
        first_name, last_name = get_first_and_last_name()
        pdf_name = (f"{first_name}{last_name}_{month_info['month_name']}_"
                    f"{month_info['year']}_invoice.pdf")
        pdf_path = os.path.join(tmpdir, pdf_name)

        build_invoice_pdf(pdf_path, month_info)
        send_email(pdf_path, month_info)



if __name__ == "__main__":
    main()



