r"""
Name : skinner.utils.py
Author : Eric Pavey - warpcat@gmail.com - www.akeric.com
Creation Date : 2021-10-23
Description :
    Various utils/tools used in different Skinner modules.
Updates:
    2021-10-23 : Refactored out of skinner.core.py
    2021-10-25 : Updating getMeshVertIds to work on joint selection.
    2021-11-01 : Adding getIconPath.
    2021-12-02 : v1.0.14 : Adding validateInteractiveNormalization.
    2021-12-15 : v1.1.0 : Adding getPreDeformedShape, getAtBindPose.
    2021-12-17 : v1.1.1 : Bugfixing getAtBindPose to return correct values.
    2021-12-30 : v1.1.2 : Updating all source to use Python3 type hint notation.
    2022-01-10 : v1.1.5 : Updating normalizeToOne to better handle floating point
        precision errors.
    2022-03-03 : v1.1.6 : Updating ProgressWindow to print stack trace if exceptions
        are encountered.  Bugfixing getAtBindPose to skip past skinClusters missing
        connected dagPose nodes.
    2022-07-18 : v1.1.10 : Updating validateInteractiveNormalization to get around
        edgcase error when running mc.skinPercent(skinCluster, normalize=True) on
        certain skinClusters.
    2024-06-04 : v1.1.11 : Bugfixing tool to properly paste weights on selected
        verts.  Specifically, updating addInfluences to not change any weights
        when influences are added.  Adding transposeWeights, to reorder SkinChunk
        influence weights based on skinCluster influence order.
"""
from __future__ import annotations # for type hinting
import re
import os
import sys
import traceback

try:
    import numpy as np
except ImportError:
    np = None
try:
    from scipy.spatial import KDTree
except ImportError:
    KDTree = None

import maya.cmds as mc
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2

#---------------------------
# Decorators:

def waitCursor(f):
    r"""
    A 'waitCursor' function decorator.
    """
    def wrapper(*args, **kwargs):
        mc.waitCursor(state=True)
        try:
            result = f(*args, **kwargs)
        finally:
            mc.waitCursor(state=False)
        return result
    return wrapper

#---------------------------
# Context Managers:

class ProgressWindow(object):
    r"""
    A context manager wrappering Maya's progressWindow functionality.
    """

    def __init__(self, totalSteps:int, enable=True, title="Applying skinning..."):
        r"""
        Parameters:
        totalSteps : int : The number of things we're iterating over.
        enable : bool : Default True : set to False to suppress this.
        title : string
        """
        self.progressSteps = 100.0 / totalSteps
        self.progress = 0.0
        self.enable = enable
        self.currentIndex = 0
        self.totalSteps = totalSteps
        self.title = title

    def __enter__(self):
        r"""
        Enter the context manager, setup the progress window:
        """
        if self.enable:
            mc.progressWindow(title=self.title,
                              progress=0, minValue=0, maxValue=100,
                              status='Not started yet...',
                              isInterruptable=True )
        return self

    def update(self, info:str) -> bool:
        r"""
        Call this every loop once the context has been entered.  It detects for
        progress window canceling, and updates the current progress.

        Parameters:
        info : string : Informative text to display

        Return : bool
        """
        ret = True
        if self.enable:
            if mc.progressWindow( query=True, isCancelled=True ):
                ret = False
            else:
                self.currentIndex += 1
                self.progress += self.progressSteps
                mc.progressWindow(edit=True, progress=int(self.progress), status='%s/%s : %s'%(self.currentIndex, self.totalSteps, info))
        return ret

    def __exit__(self, exc_type, exc_value, tb) -> bool:
        r"""
        Called when the context manager is exited, exits the progress window.
        """
        if self.enable:
            mc.progressWindow(endProgress=True)
        # If False, Raise the last exception if there is one
        if exc_type:
            tbExtract = traceback.extract_tb(tb)
            tbList = traceback.format_list(tbExtract)
            print("\nTraceback:")
            for line in tbList:
                print(line.rstrip())
            om2.MGlobal.displayError(f"Exception: {exc_value}")
        # Raise the last exception:
        return False

#-----------------
# General utils

def confirmDependencies():
    r"""
    Print information to the user about how to get numpy or scipy if they're missing,
    or if they're not running Maya in Python 3+
    """
    missingInfo = r"""----------------------------------------------------------------------------
Skinner tool requires numpy & scipy to run in Python 3.  To install them for
your version of Maya, you can follow these steps, using Python 3.7 and
Maya 2022+ as an example:

Open cmd shell **as admin**.
Then line by line (using Windows as an example):

Install the numpy & scipy packages, one at a time:
> C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe -m pip install numpy
> C:\Program Files\Autodesk\Maya2022\bin\mayapy.exe -m pip install scipy

You can optionally provide a '--target C:\some\path\to\target\dur' at the end of
the above lines if you want to install them to a custom location that Maya sees.

In either case, if presuming one of them worked, you should see (using numpy
as an example):
> Downloading numpy-1.19.5-cp37-cp37m-win_amd64.whl (13.2 MB)
> Successfully installed numpy-1.19.5

They should install here by default, unless overridden by the --target arg:
C:\Program Files\Autodesk\Maya2022\Python37\Lib\site-packages

Then in Maya's Script Editor, confirm the install:
import numpy as np
import scipy as sp
print(np.__file__)
print(sp.__file__)
# C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\numpy\__init__.py
# C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\scipy\__init__.py
----------------------------------------------------------------------------"""
    missingModule = False
    if not np:
        om2.MGlobal.displayError("Missing numpy install.")
        missingModule = True
    if not KDTree:
        om2.MGlobal.displayError("Missing scipy install.")
        missingModule = True
    if not str(sys.version).startswith("3"):
        om2.MGlobal.displayError("Not running in Python 3+, current version is: %s"%sys.version)
        missingModule = True

    if missingModule:
        print(missingInfo)

def loadPlugin():
    """
    Load the Scripted Plugin in plugin_set_weights.py, neighbor to this module.
    """
    pluginName = "plugin_set_weights.py"
    pluginDir = os.path.dirname(__file__)
    if not mc.pluginInfo(pluginName, query=True, loaded=True):
        pluginPath = os.path.join(pluginDir, pluginName)
        mc.loadPlugin(pluginPath, quiet=True)
        mc.pluginInfo(pluginName, edit=True, autoload=True)
        print("Auto-loading Skinner scripted plugin: %s"%pluginName)

def mayaArrayToNp(mayaArr:list) -> np.ndarray:
    r"""
    Currently not used.  But I wrote it, so it's staying.

    Convert the provided Maya list/array data to numpy.array.
    It's very forgiving:  You can pass in lists of floats, or MVectorArray's of
    MVectors:  Converts them all to numpy arrays:  Just need to make sure all
    elements are the same length.  If dealing with MPoint, better to convert them
    to MVector first, to get rid of the extra fourth column.
    """
    return np.append([mayaArr[0]], mayaArr[1:], axis=0)

def normalizeToOne(vals:list) -> list:
    r"""
    Return a list with the same number as the arg, where all values add to 1.0.

    Updated in 1.1.5 to better handle floating point rounding errors that can sometimes
    cause Maya to throw these warnings when setting skin weightS:
    # Warning: Some weights could not be set to the specified value. The weight total would have exceeded 1.0. #
    """
    if sum(vals) == 1.0:
        return vals

    normed = [float(val)/sum(vals) for val in vals]
    normSum = sum(normed)
    if normSum != 1.0:
        minIndex = normed.index(min(normed))
        normBuffer = normed[:]
        normBuffer.pop(minIndex)
        sumAllButMin = sum(normBuffer)
        newMinVal = 1.0 - sumAllButMin

        if newMinVal >= 0.0:
            normed[minIndex] = newMinVal
        else:
            normed[minIndex] = 0.0
            maxIndex = normed.index(max(normed))
            normed[maxIndex] += newMinVal

    return normed

def getIconPath() -> (str,None):
    """
    Return the path to the icon for this tool as a string if it's found, otherwise
    return None.  It is called icon.png, and lives next to this module.
    """
    iconPath = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.isfile(iconPath):
        return iconPath
    else:
        return None

def validateInteractiveNormalization(skinClusters:list, promptOnNonInteractiveNormalization=True):
    """
    Used in generateSkinChunks and setWeights : Skinner only works with skinCluster
    nodes with their normalizeWeights attrs set to 1 : 'interactive'.  If they're
    set to 0 'none' or 2 'post', 'things won't work too well' with this tool.

    This function will detect for these values, and prompt the user for Skinner
    to 'convert' the skinClusters to 'interactive'.  If they say no, an Exception
    will be raise, halting downstream operations.

    Parameters:
    skinClusters : list : The string names of the skinCluster nodes to query.
    promptOnNonInteractiveNormalization : bool : Default True
    """
    nonInteractive = []
    for skinCluster in skinClusters:
        if mc.getAttr('%s.normalizeWeights'%skinCluster) != 1: # 0 = none, 1 = interactive, 2 = post
            nonInteractive.append(skinCluster)

    if nonInteractive:
        print("Skinner: skinCluster nodes with their normalizeWeights attr set to 'non-interactive' values:")
        for ni in nonInteractive:
            print("    ", ni)
        if promptOnNonInteractiveNormalization:
            result = mc.confirmDialog(title="Warning",
                                      message=f"Found {len(nonInteractive)} skinCluster node(s) that don't have their 'normalizeWeights' set to 'interactive'.\n\nSkinner only supports normalized weights:\n\nDo you want skinner to auto convert your skinClusters to 'interactive' normalization?  If not, the tool will exit.\n\nIf you don't understand what this means, it's generally safe to 'Convert'.",
                                      button=("Convert", "Exit"))
            if result == "Exit":
                raise Exception("User exited tool based on incompatible skinCluster.normalizeWeight values.")
            mc.undoInfo(openChunk=True, chunkName="validateInteractiveNormalization")
            try:
                for skinCluster in nonInteractive:
                    mc.setAttr(f"{skinCluster}.normalizeWeights", 1) # 0 = none, 1 = interactive, 2 = post
                    try:
                        # There ahve been times  Maya has errored here, simply saying
                        # "No objects found.", and nothing else.  But skipping this
                        # if it fails seems to be ok,
                        mc.skinPercent(skinCluster, normalize=True) # normalize!
                    except:
                        pass
                    print("    NORM2 END")
                print("Skinner: updated the above skinCluster nodes to use 'interactive' weight normalization.")
            finally:
                mc.undoInfo(closeChunk=True)
        else:
            raise Exception(f"Found {len(nonInteractive)} skinCluster nodes that don't have their 'normalizeWeights' set to 'interactive' (1) : Skinner only supports normalized weights: Please set that normalization type, and then normalize the weights: {nonInteractive}")

def getPreDeformedShape(node:str) -> str:
    """
    Introduced 1.1.0 : For the provided node, return the pre-deformed (usually an
    intermediateObject, but not necessarily, depending on the state of that attr)
    mesh shape node name, presuming it can be found.  It must have the same vert
    count as the provided node to be accepted.  If none can be found that match this
    criteria, then the mesh shape node based on the input is returned.

    Parameters:
    node : string : The name of the (transform or shape level) mesh node.  Supports
        duplicate names if full paths are passed in.  If provided a transform node,
        it must have a single shape to query as a direct child : Multile child shapes
        isn't yet supported by skinner.

    Return : string : The full path to the pre-deformed (intermediateObject) shape
        node if it can be found, or the mesh shape node of the passed in node.
    """
    shape = None
    if mc.objectType(node) == "mesh":
        shape = mc.ls(node, long=True)
        if len(shape) > 1:
            raise Exception(f"Based on '{shape}'Found multiple nodes in the scene with the provided name: Please provide a full path: {shape}")
        shape = shape[0]
    else:
        shapes = mc.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True)
        assert shapes, f"The proided node has no (mesh) shape node: '{node}'"
        meshShapes = mc.ls(shapes, type='mesh', long=True)
        assert meshShapes, f"The proided node has no mesh shape node: '{node}'"
        assert len(meshShapes) == 1, f"The provided node '{node}' has multiple child mesh shape nodes:  Skinner doesn't (yet) support this: {meshShapes} "
        shape = meshShapes[0]

    history = mc.listHistory(shape, allConnections=True)
    if not history:
        # Doubt this would ever happen persumed we ran this on something with history,
        # but just in case:
        return shape

    # Now go searching.  Whatever we return must match this vert count:
    vertCount = mc.polyEvaluate(shape, vertex=True)

    # All mesh shapes, including the one passed in. The order appears to be a bit
    # random, which is unforunate.
    historyMesh = mc.ls(history, type='mesh', long=True)
    if len(historyMesh) == 1:
        if vertCount == mc.polyEvaluate(historyMesh[0], vertex=True):
        # Doubt this would ever happen, but just in case:
            return historyMesh[0]
        else:
            return shape

    # If we have more than one, then remove the passed in mesh shape:
    historyMesh.remove(shape)
    if len(historyMesh) == 1:
        if vertCount == mc.polyEvaluate(historyMesh[0], vertex=True):
            # Only one left, just return it
            return historyMesh[0]
        else:
            return shape

    # We have multiples.  May have their intermediateObject attr set, may not
    # we don't care, just go looking for a vert count match:
    ret = None
    for hm in historyMesh:
        if vertCount == mc.polyEvaluate(hm, vertex=True):
            ret = hm
            break
    if ret:
        return ret
    else:
        return shape

#----------
# API getters

def getMObject(stringName:str) -> om2.MObject:
    r"""
    Return an MOBject instance for the provided string node name.
    """
    selList = om2.MSelectionList()
    selList.add(stringName)
    return selList.getDependNode(0)

def getMDagPath(stringName:str) -> om2.MDagPath:
    r"""
    Return an MDagPath for the provided string name.
    """
    selList = om2.MSelectionList()
    selList.add(stringName)
    return selList.getDagPath(0)

def getMObjectForVertIndices(verts:list) -> om2.MObject:
    r"""
    Get an MObject collecting the ids for the passed in verts. Note, this MObject
    stores vert indices, it really has nothing to do with the actual mesh/verts
    themselves.  It's a weird abstraction layer, but needed to set weights via
    the API.

    Here's an example of how to interact with the returned MObject at a higher
    level, after the fact:

    importVertexCompObj = getMObjectForVertIndices(listOfVertNames) # type: om2.MObject
    if importVertexCompObj.hasFn(om2.MFn.kMeshVertComponent):
        # The above test should always be True, but it's how you'd check for it
        # on an arbitrary MObject.
        singleIdComp = om2.MFnSingleIndexedComponent(importVertexCompObj)
        elements = singleIdComp.getElements()

    Parameters:
    verts : list : The "meshName.vtx[#]' for each vertex.

    Return : MObject : The representation of these components.
    """
    if not isinstance(verts, (list,tuple)):
        verts = [verts]
    indices = [int(re.findall(r'\d+', vert)[-1]) for vert in verts]
    # https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=Maya_SDK_py_ref_class_open_maya_1_1_m_fn_single_indexed_component_html
    singleIdComp = om2.MFnSingleIndexedComponent() # type: om2.MFnSingleIndexedComponent
    # https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=Maya_SDK_py_ref_class_open_maya_1_1_m_object_html
    vertexComp = singleIdComp.create(om2.MFn.kMeshVertComponent) # type: om2.MObject
    singleIdComp.addElements(indices)
    return vertexComp

def getMFnSkinCluster(shape:(str,om2.MDagPath)):
    r"""
    Get the skin cluster for the given shape node.

    Parameters:
    shape : string/MDagPath : The shape node to query skincluster on.

    return : MFnSkinCluster : MFnSkinCluster node assigned to the mesh, or None.
        https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_anim_1_1_m_fn_skin_cluster_html
    """
    mDagPath = None
    if isinstance(shape, om2.MDagPath):
        mDagPath = shape
    mDagPath = getMDagPath(shape)
    ret = None
    mItDependencyGraph = om2.MItDependencyGraph(mDagPath.node(),
                                                om2.MItDependencyGraph.kDownstream,
                                                om2.MItDependencyGraph.kPlugLevel)
    while not mItDependencyGraph.isDone():
        mObject = mItDependencyGraph.currentNode()
        if mObject.hasFn(om2.MFn.kSkinClusterFilter):
            ret = oma2.MFnSkinCluster(mObject)
            break
        mItDependencyGraph.next()
    return ret

def getInfluenceDagPaths(meshName:str) -> list:
    r"""
    Return a list of MDagPath instances for each influence on the mesh.
    """
    shapeDatPath = getMDagPath(meshName)
    mFnSkinCluster = getMFnSkinCluster(shapeDatPath)
    return mFnSkinCluster.influenceObjects()

#----------------
# Skin related actions

def unlockInfluences( skinCluster:(str,om2.MDagPath,oma2.MFnSkinCluster) ):
    r"""
    Unlock/unhold all the influences for the provided skinCluster.

    Parameters:
    skinCluster : string/MDagPath/MFnSkinCluster : The skinCluster node to update.
    """
    if not isinstance(skinCluster, (str, bytes)):
        if isinstance(skinCluster, om2.MDagPath):
            skinCluster = skinCluster.fullPathName()
        elif isinstance(skinCluster, oma2.MFnSkinCluster):
            skinCluster = skinCluster.name()
        else:
            raise Exception("The provided type to 'skinCluster' is not supported: %s"%(type(skinCluster)))
    influences = mc.ls(mc.skinCluster(skinCluster, query=True, influence=True), type='joint', long=True)
    for infJ in influences:
        try:
            mc.setAttr(f"{infJ}.lockInfluenceWeights", 0)
        except:
            pass


def addInfluences(skinCluster:(str,om2.MDagPath,oma2.MFnSkinCluster),
                  influences:list, setToBindPose=True):
    r"""
    Currently not sure how to add influences to a skinCluster via the API, so,
    via the commands.  If any influences need to be added, the skinCluster will
    be set to the bind pose first.  Even if this is unsuccessfull, the influences
    will be added, but errors will be printed in the script editor.

    Parameters:
    skinCluster : string/MDagPath/MFnSkinCluster : The skinCluster node to update.
    influences : list : The string names or MDagPaths of the influences to append.
    """
    if not isinstance(skinCluster, (str, bytes)):
        if isinstance(skinCluster, om2.MDagPath):
            skinCluster = skinCluster.fullPathName()
        elif isinstance(skinCluster, oma2.MFnSkinCluster):
            skinCluster = skinCluster.name()
        else:
            raise Exception("The provided type to 'skinCluster' is not supported: %s"%(type(skinCluster)))
    infs = []
    for inf in influences:
        if isinstance(inf, (str, bytes)):
            infs.append(inf)
        elif isinstance(inf, om2.MDagPath):
            infs.append(inf.fullPathName())
        else:
            raise Exception("The items in influence must be string or MDagPath, instead got '%s'"%(type(inf)))

    if not isinstance(influences, (list,tuple)):
        influences = [influences]

    unlockInfluences(skinCluster)
    if setToBindPose:
        setBindPose(skinCluster)
    mc.skinCluster(skinCluster, edit=True, addInfluence=infs, weight=0.0)

def setBindPose(skinCluster:str) -> (bool,None):
    r"""
    Set the provided skinCluster to its bind pose.  If no dagPose is connected to
    the provided skinCluster, an error will be printed, and nothing done.
    If after the bindPose is set some nodes are still not at the bind pose, an
    error will be printed.

    Parameters:
    skinCluster : string : The name of the skinCluster node to set to the bind pose.

    Return : bool/None : True if all of the nodes in the dagPose were able to be set
        to the bind pose. False if not all the nodes could be set to the bind pose.
        None if there was no dagPose node to set.
    """
    dagPose = mc.listConnections("%s.bindPose"%skinCluster)
    if not dagPose:
        om2.MGlobal.displayError("skinner.setBindPose : The provided skinCluster '%s' has no connected dagPose node, unable to set to the bind pose."%skinCluster)
        return None

    notAtPose = mc.dagPose(dagPose[0], atPose=True, query=True)
    if notAtPose:
        try:
            mc.dagPose(dagPose[0], restore=True)
        except RuntimeError as e:
            print(e)
            om2.MGlobal.displayError("skinner.bindpose : Tried to set the skinCluster '%s' to it's bind pose, as defined by '%s', but failed, see above."%(skinCluster,dagPose[0]))
            return False

    return True

def getAtBindPose(skinClusters:list) -> bool:
    """
    Get if the provided skinCluster node(s) are at their bindpose.  It does this
    by querying the connected dagPose node.  If there is no dagPose node, it will
    be skipped, and the return value not changed.

    Parameter:
    skinClusters : string/list : The skinCluster nodes to query.

    Return : bool : True if all skinClustesr are at their bindPose, False if any
        one of them isn't.
    """
    if not isinstance(skinClusters, (list,tuple)):
        skinClusters = [skinClusters]
    atPose = True

    for skinCluster in skinClusters:
        if not atPose:
            break
        dagPoses = mc.listConnections(skinCluster , source=True, destination=False, type="dagPose")
        if not dagPoses:
            continue
        poses = set(dagPoses)
        for pose in poses:
            notAtPose = mc.dagPose(pose, query=True, atPose=True)
            if notAtPose:
                atPose = False
                break
    return atPose

def transposeWeights(skinChunkWeights:list[float], skinChunkInfNames:list[str], skinClusterInfNames:list[str] ):
    """
    For the passed in list of weight values from a skinChunk, transpose (reorder
    them) so that they match the same order as the influences for a given skinCluster.

    Parameters:
    skinChunkWeights : list : Each item is a sublist of floats, that is the same
        lenth as both skinChunkInfNames and skinClusterInfNames.
    skinChunkInfNames : list : The leaf influence names in the SkinChunk.
    skinClusterInfNames : list : The leaf influence names in the skinCluster.

    Return : list : Each item is the same sublist passed in to skinChunkWeights,
        but reordered to match the skinCluster influence order.
    """
    # Mostly wrote to help with debugging while authroring it.  Technically none
    # of these should be hit based on calls from the main code.
    assert len(skinChunkWeights[0]) == len(skinChunkInfNames), f"The list of weighs in skinChunkWeights ({len(skinChunkWeights[0])}) is a different length than the number of names in skinChunkInfNames ({len(skinChunkInfNames)})"
    missingSkinChunk = [name for name in skinChunkInfNames if name not in skinClusterInfNames]
    assert not missingSkinChunk, f"Found {len(missingSkinChunk)} influences in skinChunkInfNames that aren't in skinClusterInfNames: {missingSkinChunk}"
    missingSkinCluster = [name for name in skinChunkInfNames if name not in skinChunkInfNames]
    assert not missingSkinCluster, f"Found {len(missingSkinCluster)} influences in missingSkinCluster that aren't in skinChunkInfNames: {missingSkinCluster}"

    ret = []
    for chunkWeights in skinChunkWeights:
        transposed = []
        for skinClusterInf in skinClusterInfNames:
            if skinClusterInf in skinChunkInfNames:
                chunkIndex = skinChunkInfNames.index(skinClusterInf)
                transposed.append(chunkWeights[chunkIndex])
            else:
                transposed.append(0)
        ret.append(transposed)
    return ret

#-------------------
# Skin weight related getters

def getWeights(items:list) -> np.ndarray:
    r"""
    Get the influence weight data for the provided items.

    Parameters:
    items : string/list : The mesh shape / or list of verts (['meshName.vtx[#]', ...])
        to get weights for.  If verts, presumed to be all on the same mesh.  Everything
        is converted to verts.

    Return : ndarray[x][y] : Each item(x) is a sublist (y)
        for the float influence weights, for each vertex.  The weights are in
        the order provided by getInfluenceDagPaths.

    """
    # Convert from strings to api:
    verts = mc.ls(mc.polyListComponentConversion(items, toVertex=True), flatten=True, long=True)
    shapes = list(set([vert.split(".")[0] for vert in verts]))
    assert len(shapes) == 1, "getWeights : All 'items' must be part of the same mesh.  Instead, was provided items on these mesh: %s"%shapes
    meshShape = getMeshShape(verts[0].split(".")[0])
    meshDagPath = getMDagPath(meshShape)
    vertexComp = getMObjectForVertIndices(verts)

    # Now get the weight data:
    mFnSkinCluster = getMFnSkinCluster(meshDagPath)
    assert mFnSkinCluster, "%s isn't skinned"%meshShape
    # https://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__py_ref_class_open_maya_anim_1_1_m_fn_skin_cluster_html
    weights, numInfs = mFnSkinCluster.getWeights(meshDagPath, vertexComp)
    chunks = [list(weights[i:i+numInfs]) for i in range(0, len(weights), numInfs)]
    return np.array(chunks)

def getBlendWeights(items:list):
    r"""
    Get the 'blend weight' data for the provided items.  It's presumed that this
    skinCluster is set to 'Weight Blended' mode, but even if it's not, this function
    won't fail: It will return a ndarray of zero's, or whatever blend weights were
    set last.

    Parameters:
    items : string/list : The mesh shape / or list of verts (['meshName.vtx[#]', ...])
        to get weights for.  If verts, presumed to be all on the same mesh.  Everything
        is converted to verts.

    Return : ndarray[x] : The list of blendWeight values per vert.
    """
    # Convert from strings to api:
    verts = mc.ls(mc.polyListComponentConversion(items, toVertex=True), flatten=True, long=True)
    shapes = list(set([vert.split(".")[0] for vert in verts]))
    assert len(shapes) == 1, "getBlendWeights: All 'items' must be part of the same mesh.  Instead, was provided items on these mesh: %s"%shapes
    meshShape = getMeshShape(verts[0].split(".")[0])
    meshDagPath = getMDagPath(meshShape)
    vertexComp = getMObjectForVertIndices(verts)

    # Now get the weight data:
    # https://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__py_ref_class_open_maya_anim_1_1_m_fn_skin_cluster_html
    mFnSkinCluster = getMFnSkinCluster(meshDagPath)
    assert mFnSkinCluster, "%s isn't skinned"%meshShape
    blendWeights = mFnSkinCluster.getBlendWeights(meshDagPath, vertexComp)
    return np.array(blendWeights)

#-------------------
# Mesh related getters

def getMeshShape(node:str) -> str:
    r"""
    Return the mesh shape string node name for the provided transform-level node
    name.  If a shape is passed in, it is passed out.  If no mesh shape can be
    found, and exception is raised.
    """
    ret = None
    if mc.objectType(node) == "mesh":
        ret = node
    else:
        childShapes = mc.listRelatives(node, shapes=True, type='mesh', fullPath=True)
        childMesh = [mesh for mesh in childShapes if not mc.getAttr('%s.intermediateObject'%mesh)]
        if childMesh:
            ret = childMesh[0]
        else:
            raise Exception("Unable to find a mesh shape node for: %s"%(node))
    return ret

def getChildMeshShapes(mesh=None) -> list:
    r"""
    Get mesh shape nodes!

    Parameters:
    mesh : None/list : Default None : If None, use the active selection. Otherwise
        act on the provided list of mesh.  Note, that in either case, the tool
        will work on the full recursive hierarchy of what is provided, finding all
        child mesh shape nodes.

    Return : list : The mesh shape node names as string, full paths.
    """
    if not mesh:
        # Get the mesh shapes of the current selection:
        mesh = mc.listRelatives(mc.ls(selection=True, long=True), allDescendents=True,
                                fullPath=True, type="mesh", noIntermediate=True)
    else:
        # Find all the child mesh shapes of what was passed in.
        if not isinstance(mesh, (list,tuple)):
            mesh = [mesh]
        allMesh = []
        for m in mesh:
            if mc.objectType(m) == "transform":
                childMesh = mc.listRelatives(m, allDescendents=True, fullPath=True,
                                             type="mesh", shapes=True, noIntermediate=True)
                allMesh.extend(childMesh)
            elif mc.objectType(m) == "mesh":
                allMesh.append(m)
        mesh = allMesh

    # noItermediate isn't doing it's job so...
    if mesh:
        mesh = [m for m in mesh if not mc.getAttr('%s.intermediateObject'%m)]
    return mesh

#-------------------
# Vertex related getters

def getVertNormals(items) -> np.ndarray:
    r"""
    Get the worldspace vertex normals for the provided items.  Anything provided
    to items is converted to vertices.

    Parameters:
    items : string/list : The mesh shape / or list of verts (['meshName.vtx[#]', ...])
        to get weights for.  If verts, presumed to be all on the same mesh.  Everything
        is converted to verts.

    Return : ndarray[x][y] : The worldspace normals per vert.
    """
    if not isinstance(items, (list, tuple)):
        items = [items]
    vertCheck = [item for item in mc.ls(items, flatten=True, long=True) if '.vtx[' in item]
    convertedVerts =  mc.ls(mc.polyListComponentConversion([item for item in items if '.vtx[' not in item]), flatten=True, long=True)
    verts = vertCheck + convertedVerts
    shapes = list(set([vert.split(".")[0] for vert in verts]))
    assert len(shapes) == 1, "getVertNormals : All 'items' must be part of the same mesh.  Instead, was provided items on these mesh: %s"%shapes
    meshShape = getMeshShape(verts[0].split(".")[0])
    meshDagPath = getMDagPath(meshShape)
    vertexComp = getMObjectForVertIndices(verts)
    # https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_1_1_m_it_mesh_vertex_html
    iterVerts = om2.MItMeshVertex(meshDagPath, vertexComp)
    normals = []
    while not iterVerts.isDone():
        normal = iterVerts.getNormal(om2.MSpace.kWorld) # MVector
        normals.append(normal)
        iterVerts.next()
    return np.array(normals)

def getMeshVertIds(items=None) -> dict:
    r"""
    This takes the input, would could be any number of transforms (and thus all the
    child mesh shapes therein), mesh shapes, joints (for which it will find the
    related skinClusters -> their mesh) or verts in any combination thereof, and
    gets usable mesh vert IDs for SkinChunk export.

    If items is None, and nothing is selected, an AssertionError will be raised.

    Parameters:
    items : string / list / None : If None, work on the active selection.  Otherwise
        names of transforms, mesh shapes, or vert names like 'mesh.vtx[#]'

    Return : dict :keys are mesh shape names, full paths.
        Values are the vert ID#'s (as ints) that should be processed.

    """
    if not items:
        items = []
        selItems = mc.ls(selection=True, flatten=True, long=True)

        for item in selItems:
            if ".vtx[" in item:
                items.append(item)
            else:
                if mc.objectType(item) == "joint":
                    outSkinClusters = mc.listConnections(item, source=False, destination=True, type='skinCluster')
                    if outSkinClusters:
                        outSkinClusters = list(set(outSkinClusters))
                        for skinCluster in outSkinClusters:
                            mesh = mc.skinCluster(skinCluster, query=True, geometry=True)
                            if mesh:
                                for m in mesh:
                                    if m not in items:
                                        items.append(m)

                elif mc.objectType(item) == "transform":
                    children = mc.listRelatives(item, allDescendents=True, fullPath=True) # noIntermediate=True, type='mesh', don't play well together.
                    childMesh = mc.ls(children, type='mesh', noIntermediate=True, long=True)
                    if childMesh:
                        for cm in childMesh:
                            if cm not in items:
                                items.append(cm)
    else:
        if not isinstance(items, (list,tuple)):
            items = [items]
        items = mc.ls(items, flatten=True, long=True)
    assert items, "No mesh/verts are provided."
    itemsRet = {}
    nonItemsRet = {}

    for item in items:

        if ".vtx[" in item:
            # vertex component
            vertId = int(re.findall("\d+", item)[-1])
            itemName = item.split(".")[0]
            # itemName could be transform or shape level, need to convert to shape
            meshShape = None
            if mc.objectType(itemName) == "mesh":
                meshShape = itemName
            else:
                shapes = mc.listRelatives(itemName, fullPath=True,
                                          type="mesh", shapes=True, noIntermediate=True)
                if shapes: # this should alway be a thing
                    meshShape = shapes[0]

            if meshShape in itemsRet:
                if vertId not in itemsRet[meshShape]:
                    itemsRet[meshShape].append(vertId)
            else:
                itemsRet[meshShape] = [vertId]

        else:
            if mc.objectType(item) == "mesh":
                # Is mesh, add all the verts for it:
                itemsRet[item] = list(range(mc.polyEvaluate(item, vertex=True)))

            else:
                # Must be transform, find all child mesh, and add all their verts.
                childMesh = mc.listRelatives(item, allDescendents=True, fullPath=True,
                                             type="mesh", shapes=True, noIntermediate=True)
                if childMesh:
                    for cm in childMesh:
                        itemsRet[cm] = list(range(mc.polyEvaluate(cm, vertex=True)))

    # make sure all our vertIds are sorted:
    for meshShape in itemsRet:
        itemsRet[meshShape].sort()

    return itemsRet

def getConnectedVertIDs(verts:list) -> list:
    r"""
    Return a list of all connected vert ids based on the list of passed in verts.
    All verts are presumed to be on the same mesh.
    """
    if not isinstance(verts, (list, tuple)):
        verts = [verts]
    connectedVertIds = [] # np.array

    selList = om2.MSelectionList()
    verts = mc.ls(verts, flatten=True)
    for vert in verts:
        selList.add(vert)

    iterSelList = om2.MItSelectionList(selList)
    while not iterSelList.isDone():
        nodeDagPath, componentsObject = iterSelList.getComponent()
        if not componentsObject.isNull():
            iterGeo = om2.MItMeshVertex  (nodeDagPath, componentsObject)
            while not iterGeo.isDone():
                connectedIds = iterGeo.getConnectedVertices()
                connectedVertIds.extend(connectedIds)
                iterGeo.next()
        iterSelList.next()

    return sorted(list(set(connectedVertIds)))

def getVertNeighborSamples(meshShape:str, neighborSamples:int) -> dict:
    r"""
    Find all the connected neighbor verts for the provided mesh, based on the
    number of sample points.

    Parameters:
    meshShape: string : The mesh shape node to query.
    neighborSamples : int : How many points to sample on the mesh?

    Return : dict : Each key is a vert ID int index, and each value is a list of
        string names for all connected verts.
    """
    vertNeighbors = {}
    totalMeshVerts = mc.polyEvaluate(meshShape, vertex=True)
    step = int(totalMeshVerts/neighborSamples)
    if step == 0:
        step = totalMeshVerts-1
    for i in range(0, totalMeshVerts, step):
        vertNeighbors[i] = getConnectedVertIDs('%s.vtx[%s]'%(meshShape, i))
    return vertNeighbors