# example replicator jobs

"""Illustrate job_document received from job creator service"""

from amqpstorm import Connection
from textwrap import dedent

replicator_job =  dedent("""\
  {
    "replicationjob" :
      {
        "id": "0815",
        "cloud_image_description": "My Image",
        "framework": "ec2",
        "source_regions":
          {
            "us-east-1":
              {
                "account": "rjschwei"
                "target_regions": ['us-east-2', 'us-west-2', 'eu-west-3']
              },
             "cn-north-1":
               { 
                 "account": "cn-rjschwei"
                 "target_regions": ['cn-northwest-1']
               }
           }
        }
  }""")
