#!/bin/bash

# Create and deploy Ec2 with custom Ami.

usage()
{
  echo "Usage: create_infraestructure.sh [OPTIONS]"
  echo "Create and deploy Ec2 with custom Ami"
  echo "  - Create custom Amis"
  echo "  - Deploy custom Amis"
  echo "  - Create launch template"
  echo ""
  echo "Options: -ph"
  echo
  echo "    -p           Uses production account. Staging otherwise"
  echo "    -h           Shows this help"
}

REGION="us-east-1"

while getopts ph option
do
    case "${option}"
    in
        p) PRODUCTION=1 ;;
        h) usage; exit 1 ;;
        ?) echo "Unknown option: -$OPTARG" >&2; exit 1;;
    esac
done

if [ "${PRODUCTION}" == "1" ]
then
    ENVIRONMENT="production"
    PROFILE="[production profile]"
else
    ENVIRONMENT="staging"
    PROFILE="[Staging profile]"
fi

# Define all available stacks
ALL_STACKS=(
    "CreateAMI"
    "BuildAMI"
    "CreateTemplate"
)

select_stack() {
    echo "Available stacks:"
    for i in "${!ALL_STACKS[@]}"; do
        echo "[$((i+1))] ${ALL_STACKS[$i]}"
    done
    echo "[Q] Quit"
    
    while true; do
        read -p "Select a stack to deploy (1-${#ALL_STACKS[@]}) or Q to quit: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#ALL_STACKS[@]}" ]; then
            return $((choice-1))
        elif [[ "$choice" =~ ^[Qq]$ ]]; then
            echo "Exiting..."
            exit 0
        else
            echo "Invalid option. Please try again."
        fi
    done
}

cleanup() {
    echo
    echo "Deactivating virtual environment"
    deactivate
}

# init
# login to aws
aws-sso-util login

select_stack
selected_index=$?
SELECTED_STACK="${ALL_STACKS[$selected_index]}"

VENV_PATH=${VENV_PATH:-".venv"}

# Activate virtual environment
if [ -d "$VENV_PATH" ]; then
echo
    echo -e "Activating virtual environment at $VENV_PATH"
    source "$VENV_PATH/bin/activate"
else
    echo
    echo -e "\e[31mError:\e[39m Virtual environment not found at $VENV_PATH"
    exit 1
fi

trap cleanup EXIT

echo -e "Deploying stack: \e[32m$SELECTED_STACK\e[39m"
cdk deploy $SELECTED_STACK \
  --context environment_name=$ENVIRONMENT \
  --context stack_name=$SELECTED_STACK \
  --profile $PROFILE \
  --require-approval never

# Check if the deployment was successful
if [ $? -ne 0 ]; then
    echo -e "Error: Deployment of $SELECTED_STACK failed"
    exit 1
fi

if [[ $SELECTED_STACK == "CreateTemplate" ]]; then
    echo
    echo -e "\e[32mSet a new template as default?\e[39m"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        if [[ $SELECTED_STACK == "CreateTemplate" ]]; then
            SELECTED_STACK="LaunchTemplate"
        fi
        echo
        echo "Set the new template as the default."
        LAST_VERSION=$(aws ec2 describe-launch-template-versions \
          --launch-template-name ${SELECTED_STACK} \
          --query "LaunchTemplateVersions | sort_by(@, &VersionNumber) | [-1].VersionNumber" \
          --output text \
          --profile ${PROFILE} \
          --region us-east-1)
        
        echo -e "Last version: \e[32m$LAST_VERSION\e[39m"
        aws ec2 modify-launch-template \
          --launch-template-name $SELECTED_STACK \
          --default-version $LAST_VERSION \
          --profile ${PROFILE} \
          --region us-east-1
    fi
fi

echo -e "\e[32mStack $SELECTED_STACK has been deployed successfully!\e[39m"
