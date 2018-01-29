# example publisher jobs

"""Illustrate job_document received from job creator service"""

from amqpstorm import Connection
from textwrap import dedent

uploader_job = dedent("""\
  {
    "publisher_job":
      {
        "id": "0815",
        "framework": "ec2",
        "publish_regions":
          [
            {
              "account": "rjschwei",
              "target_regions": ["us-east-1", "us-east-2", "eu-west-3"]
            },
            {
              "account": "cn-rjschwei",
              "target_regions": ["cn-north-1", "cn-northwest-1"]
            }
        ]
        "share_with": ["all"]
       }
  }""")
