import sys
import os
from glob import glob
from distutils.core import setup, Extension
from Cython.Build import cythonize
import numpy

# if sys.platform == "darwin":
#     # Don't create resource files on OS X tar.
#     os.environ['COPY_EXTENDED_ATTRIBUTES_DISABLE'] = 'true'
#     os.environ['COPYFILE_DISABLE'] = 'true'

CLASSIFIERS= [
    "Development Status :: 6 - Mature",
    "Environment :: Console",
    "Environment :: X11 Applications :: Qt",
    "Intended Audience :: Developers",
    "Intended Audience :: Other Audience",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "Natural Language :: English",
    "Operating System :: MacOS",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: Scientific/Engineering :: Visualization",
    "Topic :: Software Development :: Libraries :: Python Modules",
    ]

try:
    extensions = [Extension('smartview.ctree', ['smartview/ctree.pyx']),
                  Extension('smartview.clayout', ['smartview/clayout.pyx']),
                  Extension('smartview.cstyle', ['smartview/cstyle.pyx']),
    ]

    _s = setup(
        include_package_data = True,
        ext_modules = cythonize(extensions),
        include_dirs=[numpy.get_include()],

        name = 'smartview',
        version = 0.1,
        packages = ['smartview'],

        entry_points = {"console_scripts":
                        ["smartview = smartview.ete_smartview:main"]},

        # Project uses reStructuredText, so ensure that the docutils get
        # installed or upgraded on the target machine
        package_data = {

        },

        # metadata for upload to PyPI
        author = "Jaime Huerta-Cepas",
        author_email = "jhcepas@gmail.com",
        maintainer = "Jaime Huerta-Cepas",
        maintainer_email = "jhcepas@gmail.com",
        platforms = "OS Independent",
        license = "GPLv3",
        description = "Huge tree visualization with smart zooming",
        long_description = "",
        classifiers = CLASSIFIERS,
        provides = ["smartview"],
        keywords = "tree visualization",
        url = "http://etetoolkit.org",
        download_url = "http://etetoolkit.org/static/releases/ete3/",

    )

except:
    print("\033[91m - Errors found! - \033[0m")
    raise

else:

    print("\033[92m - Done! - \033[0m")
    missing = False
