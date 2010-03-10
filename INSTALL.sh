#!/bin/bash
# $Id: INSTALL.sh,v 1.7 2010/03/10 08:14:37 o-mizuno Exp $

echo "====================================================================="
echo "                       PMAN3 installer script"
echo "====================================================================="
echo "mkdir db"
mkdir db
chmod 777 db
chmod 777 install.cgi

      echo "Making .htaccess files ..."
cat <<EOF > .htaccess
<Files ~ "\.(pl|db|sh)$">
deny from all
</Files>
EOF
cp .htaccess db/
cp .htaccess lib/
touch ./index.html ./db/index.html ./lib/index.html 
echo "Done." 
echo "====================================================================="
echo "              Please run    install.cgi    from your browser."
echo "====================================================================="
