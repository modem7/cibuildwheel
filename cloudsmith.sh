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
sudo pip install -U cloudsmith-cli

# Upload to Cloudsmith
for f in $PWD/wheelhouse/*.whl
do
  echo "Processing $f file..."
  # take action on each file. $f store current file name
  cloudsmith push python -W -k $CLOUDSMITH_API --no-republish modem7/wheels "$f"
done
