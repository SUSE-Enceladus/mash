#!/bin/bash

# Vars
MASH_SERVER_IP=localhost
MASH_SERVER_PORT=8000
BASE_URL="http://${MASH_SERVER_IP}:${MASH_SERVER_PORT}"
CURL_DEBUG_OPTS="--verbose"

#-------------------------------------#
#-     Print test result             -#
#-                                   -#
#-     $1 - Result                   -#
#-------------------------------------#
print_test_result(){
    if [ "$1" = "0" ]; then
        printf "${greenf}| passed | ${reset}\n"
    else
        printf "${redf}| failed | ${reset}\n"
    fi

}

print_test_header(){
    printf "${bluef}-----------------------------${reset}\n"
    printf "${bluef}    Test $1                  ${reset}\n"
    printf "${bluef}-----------------------------${reset}\n"

}




initializeANSI( ){

    esc="\033" # If this doesn't work, enter an ESC directly

    # Foreground Colors
    blackf="${esc}[30m";  redf="${esc}[31m";   greenf="${esc}[32m"
    yellowf="${esc}[33m"; bluef="${esc}[34m";  purplef="${esc}[35m"
    cyanf="${esc}[36m";   whitef="${esc}[37m";

    # Background Colors
    blackb="${esc}[40m";  redb="${esc}[41m";   greenb="${esc}[42m"
    yellowb="${esc}[43m"; blueb="${esc}[44m";  purpleb="${esc}[45m"
    cyanb="${esc}[46m";   whiteb="${esc}[47m";

    # Special Character Conditions
    boldon="${esc}[1m";     boldoff="${esc}[22m"
    italicson="${esc}[3m";  italicsoff="${esc}[23m"
    ulon="${esc}[4m";       uloff="${esc}[24m"
    invon="${esc}[7m";      invoff="${esc}[27m"

    # Reset to default configuration
    reset="${esc}[0m"
}

initializeANSI

###################
#  USER TESTS
###################
# User creation
TEST='User creation'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/user/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@test.com", "password": "pass"}' \
  "${URL}"
print_test_result $?

# User deletion
TEST='User deletion'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/user/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  "${URL}"
print_test_result $?

# GET user
TEST='User get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/user/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# Update user password
TEST='User password update'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/user/password"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X PUT \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@test.com", "current_password": "pass", "new_password": "newpass"}' \
  "${URL}"
print_test_result $?

# Reset user password
TEST='User password reset'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/user/password"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@test.com"}' \
  "${URL}"
print_test_result $?

###################
#  JOBS TESTS
###################
# GET jobs
TEST='Jobs get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"page": 1, "per_page": 1000 }' \
  "${URL}"
print_test_result $?

# GET job
TEST='Job get'
print_test_header "${TEST}"
JOB_ID='03c5581f-3e56-4136-a406-e067d497ead8'
URL="${BASE_URL}/v1/jobs/${JOB_ID}"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

JOB_ID='03c5581f-3e56-4136-a406-e067d497ead9'
URL="${BASE_URL}/v1/jobs/${JOB_ID}"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# DELETE JOB
TEST='Job delete'
print_test_header "${TEST}"
JOB_ID='03c5581f-3e56-4136-a406-e067d497ead8'
URL="${BASE_URL}/v1/jobs/${JOB_ID}"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

###################
#  EC2 JOB TESTS
###################
# GET EC2 job schema
TEST='EC2 Job schema get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/ec2/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  "${URL}"
print_test_result $?

# EC2 job post
TEST='EC2 job post'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/ec2/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"last_service": "create", "utctime": "now", "image":"openSUSE-Leap-15.0-EC2-HVM", "download_url": "https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.0/images/" }' \
  "${URL}"
print_test_result $?

###################
#  GCE JOB TESTS
###################
# GET GCE job schema
TEST='GCE Job schema get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/gce/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  "${URL}"
print_test_result $?

# GCE job post
TEST='GCE job post'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/gce/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"last_service": "create", "utctime": "now", "image":"openSUSE-Leap-15.0-EC2-HVM", "download_url": "https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.0/images/", "cloud_account": "my_cloud_account" }' \
  "${URL}"
print_test_result $?

###################
#  AZURE JOB TESTS
###################
# GET AZURE job schema
TEST='AZURE Job schema get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/azure/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  "${URL}"
print_test_result $?

# AZURE job post
TEST='AZURE job post'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/azure/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"last_service": "create", "utctime": "now", "image":"openSUSE-Leap-15.0-EC2-HVM", "download_url": "https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.0/images/", "cloud_account": "my_cloud_account" }' \
  "${URL}"
print_test_result $?

###################
#  ALIYUN JOB TESTS
###################
# GET ALIYUN job schema
TEST='ALIYUN Job schema get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/aliyun/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  "${URL}"
print_test_result $?

# ALIYUN job post
TEST='ALIYUN job post'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/jobs/aliyun/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"last_service": "create", "utctime": "now", "image":"openSUSE-Leap-15.0-EC2-HVM", "download_url": "https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.0/images/", "cloud_account": "my_cloud_account", "platform": "my_platform", "launch_permission": "all_permissions" }' \
  "${URL}"
print_test_result $?


###################
#  AUTH LOGIN TESTS
###################
# POST login
TEST='AUTH post login'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/auth/login"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email": "test@example.com", "password": "secretpassword123"}' \
  "${URL}"
print_test_result $?

# DELETE logout
TEST='AUTH delete logout'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/auth/logout"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# GET tokens
TEST='AUTH token get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/auth/token"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# DELETE tokens
TEST='AUTH token delete'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/auth/token"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# GET token jti
TEST='AUTH token get info jti'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/auth/token/my_jti"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# DELETE token jti
TEST='AUTH token delete jti'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/auth/token/my_jti"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# GET Azure accounts
TEST='ACCOUNTS AZURE get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/azure/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account create
TEST='ACCOUNTS AZURE create'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/azure/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"account_name": "my_account_name", "region": "myregion", "source_container": "my_source_container", "source_resource_group": "my_source_resource_group", "source_storage_account": "my_storage_account", "credentials": {"asd": "123"} }' \
  "${URL}"
print_test_result $?

# GET Azure accounts
TEST='ACCOUNTS AZURE get account'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/azure/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account update
TEST='ACCOUNTS AZURE update'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/azure/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{ "region": "myNEWregion"}' \
  "${URL}"
print_test_result $?

# DELETE account update
TEST='ACCOUNTS AZURE delete'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/azure/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# GET GCE accounts
TEST='ACCOUNTS GCE get'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/gce/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account create
TEST='ACCOUNTS GCE create'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/gce/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"account_name": "my_account_name", "region": "my_region", "testing_account": "my_testing_account", "bucket": "my_bucket", "is_publishing_account": true, "credentials": {"asd": "123"} }' \
  "${URL}"
print_test_result $?

# GET GCE account
TEST='ACCOUNTS GCE get account'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/gce/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account update
TEST='ACCOUNTS GCE update'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/gce/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{ "region": "myNEWregion"}' \
  "${URL}"
print_test_result $?

# DELETE account update
TEST='ACCOUNTS GCE delete'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/gce/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# GET EC2 accounts
TEST='ACCOUNTS EC2 get accounts'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/ec2/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account create
TEST='ACCOUNTS EC2 create'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/ec2/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"account_name": "my_account_name", "region": "my_region", "partition": "my_partition", "credentials": {"asd": "123"} }' \
  "${URL}"
print_test_result $?

# DELETE account update
TEST='ACCOUNTS EC2 delete'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/ec2/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# GET EC2 account
TEST='ACCOUNTS EC2 get account'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/ec2/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account update
TEST='ACCOUNTS EC2 update'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/ec2/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{ "region": "myNEWregion"}' \
  "${URL}"
print_test_result $?

# GET ALiyun accounts
TEST='ACCOUNTS Aliyun get accounts'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/aliyun/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account create
TEST='ACCOUNTS Aliyun create'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/aliyun/"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{"account_name": "my_account_name", "region": "my_region", "bucket": "my_bucket", "credentials": {"asd": "123"} }' \
  "${URL}"
print_test_result $?

# GET ALiyun account
TEST='ACCOUNTS Aliyun get account'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/aliyun/my_test_account"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X GET \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?

# POST account update
TEST='ACCOUNTS aliyun update'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/aliyun/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X POST \
  -H 'Authorization: my_fake_token' \
  -H 'Content-Type: application/json' \
  -d '{ "region": "myNEWregion"}' \
  "${URL}"
print_test_result $?

# DELETE account update
TEST='ACCOUNTS Aliyun delete'
print_test_header "${TEST}"
URL="${BASE_URL}/v1/accounts/aliyun/my_account_name"
curl \
  "${CURL_DEBUG_OPTS}" \
  --fail \
  -X DELETE \
  -H 'Authorization: my_fake_token' \
  "${URL}"
print_test_result $?