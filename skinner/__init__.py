"""
Skinner

Skin export/import tools for Autodesk Maya by Eric Pavey.

Changelog:
    2021-11-04 : 1.0.9 : Refactoring code in plugin_set_weights.
    2021-11-05 : 1.0.10 : Begin to refactor out scripted plugin code. Fixing up
        print timers when importing skin weights.
    2021-11-06 : 1.0.11 : Updating documentation links.
    2021-11-08 : 1.0.12 : Bugfixing SkinChunk.__init__ to better handle duplicate
        names in the scene.  Bugfixing setWeights to handle mesh and joints with
        the same names.
    2021-11-10 : 1.0.13 : Working around Maya bug where hidden mesh shape nodes
        will fail to have new skinCluster nodes generated for them.
    2021-12-02 : v1.0.14 : Updating to detect for incompatible normalizeWeights
        values, and offer to auto-correct.
    2021-12-03 : v1.0.15 : Updating core.setWeights to update the return to include
        any new influences created.  Updating core.export, core.exportTempSkin,
        core.importTempSkin, and window.App.importSkin to have consistent parameters/args
        with core.importSkin.
    2021-12-07 : v1.0.16 : Adding version info to SkinChunks. Small bugfix to
        SkinChunk.printData for numVerts.
    2021-12-13 : v1.0.17 : Updating generateSkinChunks to handle buggy imported
        FBX data that was setting skinCluster.skinningMethod to -1 (invalid).
    2021-12-15 : v1.1.0 : New feature to also query/store worldspace positions during
        export based on the pre-deformed (aka intermediateObject) shape node, in
        addition to the post-deformed one.  Bugfix to setWeights undo queue, that
        was applying bad weights when only a subset should be imported on.
    2021-12-19 : v1.1.1 : Updating SkinChunks to store local transformations and
        rotateOrder values on joints.  Updating enable/disable logic or 'Import
        Using Pre-Deformed Shape Positions?', 'Set To Bindpose?', and 'Unbind First?'.
        Bugfixing core.setWeights to properly set influences to bindpose on mesh
        that didn't yet have skinning, based on the influences stored in the SkinChunk
        data.  SkinChunks now track if they weren't at the bindpose when created.
        Bugfixing utils.getAtBindPose to return correct values.
    2021-12-30 : v1.1.2 : Updating all source to use Python3 type hint notation.
    2021-12-30 : v1.1.3 : Updating Window extras tab with separators and install path.
    2021-01-06 : v1.1.4 : Updating core.setWeights skinCluster smoothing code with
        a fixed tolerance value.
    2021-01-10 : v1.1.5 : Updating utils.normalizeToOne to better handle floating
        point precision errors.
    2022-03-03 : v1.1.6 : Updating core.ProgressWindow to print stack trace if
        exceptions are encountered.  Bugfixing core.getAtBindPose to skip past
        skinClusters missing connected dagPose nodes.'
    2022-03-09 : v1.1.7 :  New options to set the post-skinning smoothing
        'weight difference threhold' value.  Changing the default post smooth diff
        value from .01 to .25, to help resolve odd skinning bugs.
    2022-03-31 : v1.1.8 : Bugfixing string formatting error in core -> setWeights.
    2022-05-18 : v1.1.9 : Updating core.closestPointKdTree to allow numNeighbors=1.
        Before that it would be auto-set to 2, based on my not understanding how
        the ndarray return values worked.  Also updating it to support older versions
        of KDTree that don't have the 'workers' arg.
    2022-07-18 :  v1.1.10 : Updating validateInteractiveNormalization to get around
        edgcase error when running mc.skinPercent(skinCluster, normalize=True) on
        certain skinClusters.
    2024-06-04 : v1.1.11 : Bugfixing tool to properly paste weights on selected
        verts.  Specifically:
        utils.py : updating addInfluences to not change any weights when influences
            are added.  Adding transposeWeights, to reorder SkinChunk influence
            weights based on skinCluster influence order.
        core.py :  updating setWeights to leverage the new utils.transposeWeights
            to sort SkinChunk weights in the same order as the influences on the
            skinCluster. Also raising more expections if 'selectVertsOnly' is set
            and operations would happen that would change the skinning.  Various
            verbose logging formatting changes.
    2024-06-10 : v1.2.0 : window.py: Rearranging some of the Import tab  UI elements.
        Bugfixing App.importSkin : It wasn't closing the undoChunk.  Adding the
        'Auto-Fix Broken skinCluster' to the 'Extras' tab.  Updating tooltips, making
        multi-line.
        core.py : Setting setWeights unskinFirst default to False, was True. Updating
        the undoChunk closing code with specific names.  Adding regenrateSkinCluster,
        adding new tempFilePath arg, and kwargs capturing to both exportTempSkin
        and importTempSkin.
        utils.py : Updating setBindPose : "it stopped working", and now needs a
        'g' (global) arg set True.
"""
__author__ = "Eric Pavey"
__version__ = "1.2.0"
__source__ = "https://github.com/AKEric/skinner"
__documentation__ = "https://github.com/AKEric/skinner/blob/main/README.md"
__licence__ = "https://github.com/AKEric/skinner/blob/main/LICENSE.md"