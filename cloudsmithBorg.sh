#/bin/bash

# Variables
export CLOUDSMITH_API="${CLOUDSMITH_API:-}"

# Apply extra cron if it's set
if [ -n CLOUDSMITH_API ]
then
    echo "Enter Cloudsmith API token: "
    read CLOUDSMITH_API
fi

# Prerequesites
sudo python3 -m pip install -U cloudsmith-cli

# Upload to Cloudsmith
cd wheelhouse/
for f in *.whl
do
  echo "Processing $f file..."
  cloudsmith push python -W -k $CLOUDSMITH_API --no-republish borgmatic-collective/borgmatic "$f"
done
