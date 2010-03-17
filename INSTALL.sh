#!/bin/bash
# $Id: INSTALL.sh,v 1.12 2010/03/17 03:35:19 o-mizuno Exp $

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
cat <<EOF > ./index.html
<head><meta http-equiv="refresh" CONTENT="0;URL=./pman3.cgi"></head>
<body><a href="./pman3.cgi">PMAN3</a></body>
EOF
echo "Done." 
echo "====================================================================="
echo "              Please run    install.cgi    from your browser."
echo "====================================================================="
