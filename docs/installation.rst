Installation
============

:code:`yt-napari` requires both :code:`yt` and :code:`napari`. We recommend that you install both of these before installing :code:`yt-napari`.

1. (optional) install :code:`yt` and :code:`napari`
***************************************************

If you skip this step, the installation in the following section will only install the minimal package requirements for :code:`yt` or :code:`napari`, in which case you will likely need to manually install some packages. So if you are new to either package, or if you are installing in a clean environment, it may be simpler to  install these packages first.

For :code:`napari`,

.. code-block:: bash

    pip install napari[all]

will install :code:`napari` with the default :code:`Qt` backend (see `here <https://napari.org/tutorials/fundamentals/installation#choosing-a-different-qt-backend>`_ for how to choose between :code:`PyQt5` or :code:`PySide2`).

For :code:`yt`, you will need :code:`yt>=4.0.1` and any of the optional dependencies for your particular workflow. If you know that you'll need more than the base `yt` install, you can install the full suite of dependent packages with

.. code-block:: bash

    pip install yt[full]

See the :code:`yt` `documentation <https://yt-project.org/doc/installing.html#leveraging-optional-yt-runtime-dependencies>`_ for more information. If you're not sure which packages you'll need but don't want the full yt installation, you can proceed to the next step and then install any packages as needed (you will receive error messages when a required package is missing).

2. install :code:`yt-napari`
****************************

You can install the `yt-napari` plugin with minimal dependencies using:

.. code-block:: bash

    pip install yt-napari

To include optional dependencies required for loading sample data:

.. code-block:: bash

    pip install yt-napari[full]

If you are missing either :code:`yt` or :code:`napari` (or they need to be updated), the above installation will fetch and run a minimal installation for both.

To install the latest development version of the plugin instead, use:

.. code-block:: bash

    pip install git+https://github.com/data-exp-lab/yt-napari.git
