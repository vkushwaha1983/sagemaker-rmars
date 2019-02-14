import boto3
import re
import os
import wget
import time
from time import gmtime, strftime
import sys
import json

# role = 'sagemaker-bring-your-algor-training-job'
role ='arn:aws:iam::237320763645:role/service-role/AmazonSageMaker-ExecutionRole-20190128T145156'
bucket = 'sagemaker-batchdeploy'
prefix = 'sagemaker/mars'
region ='ap-south-1'
account = '237320763645'


print(role)
start = time.time()


        
s3 = boto3.client('s3')
# create unique job name 
r_job = 'sagemaker-bring-algor' + time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

print("Training job", r_job)

r_training_params = {
    "RoleArn": role,
    "TrainingJobName": r_job,
    "AlgorithmSpecification": {
        "TrainingImage": '{}.dkr.ecr.{}.amazonaws.com/sagemaker-rmars:latest'.format(account, region),
        "TrainingInputMode": "File"
    },
    "ResourceConfig": {
        "InstanceCount": 1,
        "InstanceType": "ml.m4.xlarge",
        "VolumeSizeInGB": 10
    },
    "InputDataConfig": [
        {
            "ChannelName": "train",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": "s3://{}/{}/train".format(bucket, prefix),
                    "S3DataDistributionType": "FullyReplicated"
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None"
        }
    ],
    "OutputDataConfig": {
        "S3OutputPath": "s3://{}/{}/output".format(bucket, prefix)
    },
    "HyperParameters": {
        "target": "Sepal.Length",
        "degree": "2"
    },
    "StoppingCondition": {
        "MaxRuntimeInSeconds": 60 * 60
    }
}
# create the Amazon SageMaker training job
sm = boto3.client('sagemaker')
sm.create_training_job(**r_training_params)

status = sm.describe_training_job(TrainingJobName=r_job)['TrainingJobStatus']
print(status)
sm.get_waiter('training_job_completed_or_stopped').wait(TrainingJobName=r_job)
status = sm.describe_training_job(TrainingJobName=r_job)['TrainingJobStatus']
print("Training job ended with status: " + status)
if status == 'Failed':
    message = sm.describe_training_job(TrainingJobName=r_job)['FailureReason']
    print('Training failed with the following error: {}'.format(message))
    raise Exception('Training job failed')


end = time.time()
print(end - start)