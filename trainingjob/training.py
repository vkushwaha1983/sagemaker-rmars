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

train_file = 'iris.csv'
boto3.Session().resource('s3').Bucket(bucket).Object(os.path.join(prefix, 'train', train_file)).upload_file(train_file)
 
        
s3 = boto3.client('s3')
# create unique job name 
r_job = 'sagemaker-bring-algor' + time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

print("Training job", r_job)

r_training_params = {
    "RoleArn": role,
    "TrainingJobName": r_job,
    "AlgorithmSpecification": {
        "TrainingImage": '{}.dkr.ecr.{}.amazonaws.com/sagemakerrmars:latest'.format(account, region),
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
#################################

r_hosting_container = {
    'Image': '{}.dkr.ecr.{}.amazonaws.com/sagemakerrmars:latest'.format(account, region),
    'ModelDataUrl': sm.describe_training_job(TrainingJobName=r_job)['ModelArtifacts']['S3ModelArtifacts']
}

create_model_response = sm.create_model(
    ModelName=r_job,
    ExecutionRoleArn=role,
    PrimaryContainer=r_hosting_container)

print(create_model_response['ModelArn'])

##########################

r_endpoint_config = 'DEMO-r-byo-config-' + time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
print(r_endpoint_config)
create_endpoint_config_response = sm.create_endpoint_config(
    EndpointConfigName=r_endpoint_config,
    ProductionVariants=[{
        'InstanceType': 'ml.m4.xlarge',
        'InitialInstanceCount': 1,
        'ModelName': r_job,
        'VariantName': 'AllTraffic'}])

print("Endpoint Config Arn: " + create_endpoint_config_response['EndpointConfigArn'])


#Check if endpoint needs to be created or updated

r_endpoint = 'sagemaker-endpoint'
print(r_endpoint)

endpointname =sm.list_endpoints(NameContains=r_endpoint)

if endpointname['Endpoints']==[]:
    create_endpoint_response = sm.create_endpoint(EndpointName=r_endpoint,EndpointConfigName=r_endpoint_config)
    print(create_endpoint_response['EndpointArn'])
elif endpointname['Endpoints'][0]['EndpointStatus']=='InService': 
     sm.update_endpoint(EndpointName=r_endpoint,EndpointConfigName=r_endpoint_config)
else :
    print(r_endpoint)


resp = sm.describe_endpoint(EndpointName=r_endpoint)
status = resp['EndpointStatus']
print("Status: " + status)

try:
    sm.get_waiter('endpoint_in_service').wait(EndpointName=r_endpoint)
finally:
    resp = sm.describe_endpoint(EndpointName=r_endpoint)
    status = resp['EndpointStatus']
    print("Arn: " + resp['EndpointArn'])
    print("Status: " + status)

    if status != 'InService':
        raise Exception('Endpoint creation did not succeed')

end = time.time()
print(end - start)