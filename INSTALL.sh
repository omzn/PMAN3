#!/bin/bash
# $Id: INSTALL.sh,v 1.4 2010/03/10 06:19:10 o-mizuno Exp $

echo "====================================================================="
echo "                       PMAN3 installer script"
echo "====================================================================="
echo "mkdir db"
mkdir db
chmod 777 db
echo "Making .htaccess files ..."
cat <<EOF > .htaccess
<Files ~ "\.(pl|db|sh)$">
deny from all
</Files>
EOF
cp .htaccess db/ lib/
touch ./index.html ./db/index.html ./lib/index.html 
echo "Done." 
echo "====================================================================="
echo "              Please run    install.cgi    from your browser."
echo "====================================================================="
