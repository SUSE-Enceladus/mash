from mash.services.database.models import (
    User,
    Token,
    EC2Account,
    EC2Group,
    EC2Region,
    GCEAccount,
    AzureAccount,
    Job,
    OCIAccount
)


def test_user_model():
    user = User(
        email='user1@fake.com'
    )
    user.set_password('password')
    assert user.check_password('password')
    assert user.__repr__() == '<User user1@fake.com>'


def test_token_model():
    token = Token(
        jti='12345',
        token_type='access',
        user_id='1',
        expires=None
    )
    assert token.__repr__() == '<Token 12345>'


def test_ec2_account_model():
    account = EC2Account(
        name='acnt1',
        partition='aws',
        region='us-east-1',
        user_id='1'
    )
    assert account.__repr__() == '<EC2 Account acnt1>'


def test_ec2_group_model():
    group = EC2Group(
        name='group1',
        user_id='1'
    )
    assert group.__repr__() == '<EC2 Group group1>'


def test_ec2_region_model():
    region = EC2Region(
        name='us-east-99',
        helper_image='ami-1234567890',
        account_id='1'
    )
    assert region.__repr__() == '<EC2 Region us-east-99>'


def test_gce_account_model():
    account = GCEAccount(
        name='acnt1',
        bucket='images',
        region='us-east1',
        user_id='1'
    )
    assert account.__repr__() == '<GCE Account acnt1>'


def test_azure_account_model():
    account = AzureAccount(
        name='acnt1',
        region='us-east1',
        source_container='sc1',
        source_resource_group='srg1',
        source_storage_account='ssa1',
        destination_container='dc2',
        destination_resource_group='drg2',
        destination_storage_account='dsa2',
        user_id='1'
    )
    assert account.__repr__() == '<Azure Account acnt1>'


def test_job_model():
    job = Job(
        job_id='12345678-1234-1234-1234-123456789012',
        last_service='test',
        utctime='now',
        image='test_image_oem',
        download_url='http://download.opensuse.org/repositories/Cloud:Tools/images',
        user_id='1'
    )

    job.data = {'test': 'data'}
    assert job.data['test'] == 'data'

    job.errors = ['Rut ro, Something bad happened.', 'Another error.']
    assert job.errors[0] == 'Rut ro, Something bad happened.'
    assert job.errors[1] == 'Another error.'

    assert job.__repr__() == '<Job 12345678-1234-1234-1234-123456789012>'


def test_oci_account_model():
    account = OCIAccount(
        name='acnt1',
        bucket='images',
        region='us-phoenix-1',
        user_id='1',
        availability_domain='Omic:PHX-AD-1',
        compartment_id='ocid1.compartment.oc1..',
        oci_user_id='ocid1.user.oc1..',
        tenancy='ocid1.tenancy.oc1..'
    )
    assert account.__repr__() == '<OCI Account acnt1>'
