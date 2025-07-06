# Periodic Invoice Generator

Invoice generator that is deployed to AWS Lambda.
Once the invoice is generated, it automatically sends this in an email, and it sends this periodically in a specified time-period (e.g. last day of each month).
It also saves the invoice into S3.
