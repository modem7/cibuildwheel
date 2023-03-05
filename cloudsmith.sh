#/bin/bash

# Variables
export CLOUDSMITH_API="${CLOUDSMITH_API:-}"

# Ask for Cloudsmith API if not already set
if [ -n CLOUDSMITH_API ]
then
    echo 'https://cloudsmith.io/user/settings/api/'
    echo "Enter Cloudsmith API token: "
    read CLOUDSMITH_API
fi

# Prerequesites
echo "==> Installing prerequisites"
sudo python3 -m pip install -U cloudsmith-cli

# Upload to Cloudsmith
echo "==> Uploading wheels to Cloudsmith"
cd wheelhouse/
for f in wheelhouse/*.whl
do
  echo "Processing $f file..."
  cloudsmith push python -W -k $CLOUDSMITH_API --no-republish modem7/wheels "$f"
done

# Deleting wheels
echo "==> Deleting wheels now they've been uploaded"
rm -rf wheelhouse/*.whl

exit 0