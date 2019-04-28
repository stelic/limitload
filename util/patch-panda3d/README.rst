Patches for Panda3D
===================

This is a collection of patches (if any) to the Panda3D code
necessary to get the game running as intended. All the patches
are made to be submitted upstream, so if currently there aren't
any left in this directory, then all submissions were accepted.

To apply the patches, go into the Panda3D repository directory
and execute for each patch file::

    patch -p1 -i <game_directory>/util/patch-panda3d/<name>.patch

