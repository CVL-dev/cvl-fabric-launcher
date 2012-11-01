#!/bin/bash

set -x
set -e

mkdir -p /opt/src
cd /opt/src

wget -c http://www.python.org/ftp/python/2.7.3/Python-2.7.3.tgz
wget -c http://downloads.sourceforge.net/project/modules/Modules/modules-3.2.9/modules-3.2.9c.tar.gz
wget -c http://downloads.sourceforge.net/wxpython/wxPython-src-2.8.12.1.tar.bz2

yum -y install gcc glibc glibc-devel libgcc  \
               ncurses-libs ncurses-devel \
               readline readline-devel \
               zlib zlib-devel \
               bzip2-libs bzip2-devel \
               gdbm gdbm-devel \
               sqlite sqlite-devel \
               db4 db4-devel \
               openssl openssl-devel \
               libX11 libX11-devel \
               tk tk-devel \
               gcc-c++ \
               gtk2-devel \
               gtk2-engines \
               glib2-devel \
               mesa-libGL mesa-libGL-devel \
               mesa-libGLU mesa-libGLU-devel \
               mesa-libGLw mesa-libGLw-devel \
               gtkglext-libs gtkglext-devel \
               gimp-libs gimp-devel \
               gvfs \
               atk-devel \
               pango-devel \
               cairo-devel \
               freetype-devel \
               fontconfig-devel \
               libcanberra-gtk2 \
               PackageKit-gtk-module


tar zxf modules-3.2.9c.tar.gz
cd modules-3.2.9
./configure --prefix=/opt/sw/64bit/centos/modules/3.2.9c --with-tcl-lib=/usr/lib64 --with-tcl-inc=/usr/include
make
make install
echo ". /opt/sw/64bit/centos/modules/3.2.9c/Modules/3.2.9/init/bash" >> /etc/bash.bashrc
cd ..

tar zxf Python-2.7.3.tgz
cd Python-2.7.3

# Make sure that the ssl module builds:
sed -i 's@#_socket socketmodule.c@_socket socketmodule.c@g' 											/opt/src/Python-2.7.3/Modules/Setup.dist
sed -i 's@#_ssl _ssl.c \\@_ssl _ssl.c \\@g' 													/opt/src/Python-2.7.3/Modules/Setup.dist
sed -i 's@#	-DUSE_SSL -I$(SSL)/include -I$(SSL)/include/openssl \\@       -DUSE_SSL -I$(SSL)/include -I$(SSL)/include/openssl \\@g' 	/opt/src/Python-2.7.3/Modules/Setup.dist
sed -i 's@#	-L$(SSL)/lib -lssl -lcrypto@       -L$(SSL)/lib -lssl -lcrypto@g' 								/opt/src/Python-2.7.3/Modules/Setup.dist

./configure --prefix=/opt/sw/64bit/centos/python/2.7.3 --enable-shared
make
make install
cd ..

mkdir /opt/sw/64bit/centos/modules/3.2.9c/Modules/3.2.9/modulefiles/python

cat > /opt/sw/64bit/centos/modules/3.2.9c/Modules/3.2.9/modulefiles/python/2.7.3 <<EOF
#%Module1.0#####################################################################

module-whatis "Python 2.7.3"

prepend-path PATH               /opt/sw/64bit/centos/python/2.7.3/bin

setenv PYTHONPATH               /opt/sw/64bit/centos/python/2.7.3/lib/python2.7/site-packages
prepend-path LD_LIBRARY_PATH    /opt/sw/64bit/centos/python/2.7.3/lib

prepend-path PKG_CONFIG_PATH    /opt/sw/64bit/centos/python/2.7.3/lib/pkgconfig/ 
EOF


. /opt/sw/64bit/centos/modules/3.2.9c/Modules/3.2.9/init/bash

module load python/2.7.3




tar jxf wxPython-src-2.8.12.1.tar.bz2

cd wxPython-src-2.8.12.1
export WXDIR=`pwd`
mkdir bld
cd bld

../configure --prefix=/opt/sw/64bit/centos/wxpython/2.8.12.1 \
             --with-gtk \
             --with-gnomeprint \
             --with-opengl \
             --enable-debug \
             --enable-debug_gdb \
             --enable-geometry \
             --enable-graphics_ctx \
             --enable-sound --with-sdl \
             --enable-mediactrl \
             --enable-display \
             --enable-unicode

make
make -C contrib/src/gizmos
make -C contrib/src/stc
make install
make -C contrib/src/gizmos install
make -C contrib/src/stc install


mkdir /opt/sw/64bit/centos/modules/3.2.9c/Modules/3.2.9/modulefiles/wxpython

cat > /opt/sw/64bit/centos/modules/3.2.9c/Modules/3.2.9/modulefiles/wxpython/2.8.12.1 <<EOF
#%Module1.0#####################################################################

module-whatis "wx 2.8.12.1-i686"

prepend-path PATH               /opt/sw/64bit/centos/wxpython/2.8.12.1/bin
prepend-path LD_LIBRARY_PATH    /opt/sw/64bit/centos/wxpython/2.8.12.1/lib
EOF

module load wxpython/2.8.12.1

cd $WXDIR/wxPython

python setup.py build_ext --inplace --debug
python setup.py install


# Do not use the system's easy_install, otherwise pip will be installed
# into the system's Python 2.6 directory, not our custom 2.7.3 directory.

curl http://python-distribute.org/distribute_setup.py | python
curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python

pip install ssh
pip install pycrypto
pip install appdirs
pip install psutil

echo
echo "Log out and log in again to load the modules environment."
echo
echo "Try: module load python wxpython"
echo
echo
