# example publisher jobs

"""Illustrate job_document received from job creator service"""

from amqpstorm import Connection
from textwrap import dedent

uploader_job = dedent("""\
  {
    "publisherjob":
      {
        "id": "0815",
        "framework": "ec2",
        "publish_regions":
          {
            "us-east-1": "rjschwei",
            "us-east-2": "rjschwei",
            "eu-west-3": "rjschwei",
            "cn-north-1": "cn-rjschwei"
            "cn-northwest-1": "cn-rjschwei"
          }
        "share_with": ["all"]
       }
  }""")
