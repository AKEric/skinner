r"""
Name : skinner.plugin_set_weights.py
Author : Eric Pavey - warpcat@gmail.com - www.akeric.com
Creation Date : 2019-09-28
Description :
    Skin weight setter plugin.

    For the UI, see skinner.window.py
    To load the plugin manually, see skinner.utils.loadPlugin()

    Much learning around querying/setting skinCluster data via Maya API was found
    from these sources:
    https://gist.github.com/utatsuya/a95afe3c5523ab61e61b
    http://ueta.hateblo.jp/entry/2015/08/24/102937
    Other links:
    http://www.charactersetup.com/tutorial_skinWeights.html

Updates:
    None
"""
import re

import maya.cmds as mc
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2

# Doing this, or any other import method, will break utils.loadPlugin()  Why?
#from .utils import getMDagPath, getMObjectForVertIndices, getMFnSkinCluster

#------------

# Must do, to register API2.0 commands correctly.  Secret Maya magic.
maya_useNewAPI = True

#------------
# Duplicates from the utils.py module, to get around bugs in utils.loadPlugin()

def getMDagPath(stringName):
    r"""
    Return an MDagPath for the provided string name.
    """
    selList = om2.MSelectionList()
    selList.add(stringName)
    return selList.getDagPath(0)

def getMObjectForVertIndices(verts):
    r"""
    Get an MObject collecting the ids for the passed in verts. Note, this MObject
    stores vert indices, it really has nothing to do with the actual mesh/verts
    themselves.  It's a weird abstraction layer.

    Parameters:
    verts : list : The "meshName.vtx[#]' for each vertex.

    Return : MObject : The representation of these components.
    """
    if not isinstance(verts, (list,tuple)):
        verts = [verts]
    indices = [int(re.findall(r'\d+', vert)[-1]) for vert in verts]
    singleIdComp = om2.MFnSingleIndexedComponent()
    vertexComp = singleIdComp.create(om2.MFn.kMeshVertComponent) # MObject
    singleIdComp.addElements(indices)
    return vertexComp

def getMFnSkinCluster(shape):
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

#------------

class SkinnerSetWeights(om2.MPxCommand):
    r"""
    The class that enables us to set the skinner weights, and supports undo.
    https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_1_1_m_px_command_html

    Basically a big wrapper around MFnSkinCluster.setWeights & .setBlendWeights
    so as to support Maya's undo.  Not a lot of magic in here.
    """
    commandName = "setSkinnerWeights"
    flag_meshPath = "-mp";         flag_meshPathLong = "-meshPath"
    flag_importVertNames = "-ivn"; flag_importVertNamesLong = "-importVertNames"
    flag_infIndexes = "-ii";       flag_infIndexesLong = "-infIndexes"
    flag_weights = "-w";           flag_weightsLong = "-weights"
    flag_blendWeights = "-bw";     flag_blendWeightsLong = "-blendWeights"
    flag_help = "-h";              flag_helpLong = "-help"

    helpText = r"""Synopsis: setSkinnerWeights [flags]
Flags:
 -mp -meshPath        : String             : Required : The path (name) of the mesh shape to import skinner weights on.  Like :"|someGrp|someMesh|someMeshShape", or just "someMeshShape" if the name is unique.
-ivn -importVertNames : String (multi-use) : Required : The string names of all the verts to import all the skinner weights on.  In the form: ["someMeshShape.vtx[#], ...]
 -ii -infIndexes      : Int (multi-use)    : Required : The indices representing each influence joint affecting the meshPath.
  -w -weights         : Float (multi-use)  : Required : The float weight values for all verts / influences chained together, in vertx/influence order, to be imported.
 -bw -blendWeights    : Float (multi-use)  : Optional : The float blendWeight values for all verts being imported on (used if the skinCluster 'Skinning Method' is 'Weight Blended').  If not provided, they will be all set to zero.
  -h -help"""

    #-------------

    @classmethod
    def cmdCreator(cls):
        # Plugin Bolierplate.
        return cls()

    @staticmethod
    def createSyntax():
        r"""
        Plugin Bolierplate.
        The syntax (flags/args) that our plugin accepts.
        """
        # http://download.autodesk.com/us/maya/2010help/API/class_m_syntax.html
        syntax = om2.MSyntax()
        syntax.addFlag(SkinnerSetWeights.flag_meshPath, SkinnerSetWeights.flag_meshPathLong, syntax.kString)
        syntax.addFlag(SkinnerSetWeights.flag_importVertNames, SkinnerSetWeights.flag_importVertNamesLong, syntax.kString)
        syntax.makeFlagMultiUse(SkinnerSetWeights.flag_importVertNames)
        syntax.addFlag(SkinnerSetWeights.flag_infIndexes, SkinnerSetWeights.flag_infIndexesLong, syntax.kLong)
        syntax.makeFlagMultiUse(SkinnerSetWeights.flag_infIndexes)
        syntax.addFlag(SkinnerSetWeights.flag_weights, SkinnerSetWeights.flag_weightsLong, syntax.kDouble)
        syntax.makeFlagMultiUse(SkinnerSetWeights.flag_weights)
        syntax.addFlag(SkinnerSetWeights.flag_blendWeights, SkinnerSetWeights.flag_blendWeightsLong, syntax.kDouble)
        syntax.makeFlagMultiUse(SkinnerSetWeights.flag_blendWeights)
        syntax.addFlag(SkinnerSetWeights.flag_help, SkinnerSetWeights.flag_helpLong)

        return syntax

    #-------------
    # Superclass overides:

    def __init__(self):
        r"""
        Init our command!
        """
        om2.MPxCommand.__init__(self)
        # Set in self.doIt:
        self.newValue = {}
        # Set in self.action:
        self.prevValue = {}

    def doIt(self, argList):
        r"""
        Plugin Bolierplate.
        Executed when calling to the command.

        Parameters:
        argList : MArgList : https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_1_1_m_arg_list_html
        """

        # https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_1_1_m_arg_database_html
        argData = om2.MArgDatabase(self.syntax(), argList)

        if argData.isFlagSet(SkinnerSetWeights.flag_help):
            # This works, but prints it like a single-line list.
            #self.setResult(SkinnerSetWeights.helpText)
            om2.MGlobal.displayInfo(SkinnerSetWeights.helpText)
            return True

        #---------------------------
        # Parse input args

        # meshPath : string  : mesh shape full path : Becomes MDagPath (mesh shape)
        meshPath = None
        if argData.isFlagSet(SkinnerSetWeights.flag_meshPath):
            meshPath = argData.flagArgumentString(SkinnerSetWeights.flag_meshPath, 0)
        else:
            mc.error("%s must be the path to a mesh shape."%SkinnerSetWeights.flag_meshPathLong)
            return
        #print("MESH PATHS", meshPath)

        # importVertNames : string array : list of import vert string names :
        #    Becomes MObject for each vert to import weights on
        importVertNames = []
        if argData.isFlagSet(SkinnerSetWeights.flag_importVertNames):
            numVerts = argData.numberOfFlagUses(SkinnerSetWeights.flag_importVertNames)
            for i in range(numVerts):
                flagArgList = argData.getFlagArgumentList(SkinnerSetWeights.flag_importVertNames, i)
                if len(flagArgList):
                    importVertNames.append(flagArgList.asString(0))
        else:
            mc.error("%s must be provided a list of vertext names."%SkinnerSetWeights.flag_importVertNamesLong)
            return
        #print("VERTS: %s"%importVertNames)

        # infIndexes : int array :  The 'index for influence object' for each joint
        #    on the skin cluster : Becomes MIntArray
        infIndexes = []
        if argData.isFlagSet(SkinnerSetWeights.flag_infIndexes):
            numInfs = argData.numberOfFlagUses(SkinnerSetWeights.flag_infIndexes)
            for i in range(numInfs):
                flagArgList = argData.getFlagArgumentList(SkinnerSetWeights.flag_infIndexes, i)
                if len(flagArgList):
                    infIndexes.append(flagArgList.asInt(0))
        else:
            mc.error("%s must be provided a list int influence IDs."%SkinnerSetWeights.flag_infIndexesLong)
            return
        #print("INF INDICES: %s"%infIndexes)

        # weights : float array : All the weights for every very for every influence,
        #    in one giant long chain. : Becomes  MDoubleArray.

        weights = []
        if argData.isFlagSet(SkinnerSetWeights.flag_weights):
            numWeights = argData.numberOfFlagUses(SkinnerSetWeights.flag_weights)
            for i in range(numWeights):
                flagArgList = argData.getFlagArgumentList(SkinnerSetWeights.flag_weights, i)
                if len(flagArgList):
                    weights.append(flagArgList.asFloat(0))
        else:
            mc.error("%s must be provided a list float skin weight values."%SkinnerSetWeights.flag_weightsLong)
            return
        #print("WEIGHTS: %s"%weights)

        blendWeights = []
        if argData.isFlagSet(SkinnerSetWeights.flag_blendWeights):
            numBlendWeights = argData.numberOfFlagUses(SkinnerSetWeights.flag_blendWeights)
            for i in range(numBlendWeights):
                flagArgList = argData.getFlagArgumentList(SkinnerSetWeights.flag_blendWeights, i)
                if len(flagArgList):
                    blendWeights.append(flagArgList.asFloat(0))
            if not len(blendWeights) == len(importVertNames):
                mc.error("If 'blendWeights' are provided, their length (%s) must be the same as the number of 'importVertNames' passed in (%s)"%(len(blendWeights), len(importVertNames)))
                return

        #print("BLEND WEIGHTS: %s"%blendWeights)

        #--------------------------------------------
        # Store the values that will be applied:
        self.newValue = {"meshDagPath":getMDagPath(meshPath),
                         "importVertexCompObj":getMObjectForVertIndices(importVertNames),
                         "infIndexes":om2.MIntArray(infIndexes),
                         "arrayWeights":om2.MDoubleArray(weights),
                         "arrayBlendWeights":om2.MDoubleArray(blendWeights),
                         "mfnSkinCluster":getMFnSkinCluster(meshPath)}

        return self.redoIt()

    def redoIt(self):
        r"""
        Plugin Bolierplate.
        Any actual work the command should do is done in here,
        during either the initial execution iside doIt, or when a 'redo' is executed
        after an undo.
        """
        # self.action is what sets self.prevValue:
        self.action(self.newValue)

    def undoIt(self):
        r"""
        Plugin Bolierplate.
        Reset the state if undo is executed.
        """
        self.action(self.prevValue)

    def isUndoable(self):
        return True

    #----------
    # Custom methods, not API overides.  This is where your custom code does to
    # do all the plugin-related work:

    def action(self, values):
        r"""
        Do the work on the saved state, whether it's the 'previous
        state' (undoIt), or the 'new state' (doIt/redoIt).

        Parameters:
        values : dict : The values to set for this action.  Either self.newValue
            or self.prevValue
        """
        self.prevValue = self.newValue.copy()

        # Turn into variables just for readability
        mFnSkinCluster = values["mfnSkinCluster"]
        meshDagPath = values["meshDagPath"]
        importVertexCompObj = values["importVertexCompObj"]
        infIndexes = values["infIndexes"]
        arrayWeights = values["arrayWeights"]
        arrayBlendWeights = values["arrayBlendWeights"]

        # Setting the new weights returns the current weights, which we can then save
        # as part of the 'previous values':
        oldArrayWeights = mFnSkinCluster.setWeights(meshDagPath, importVertexCompObj, infIndexes, arrayWeights, returnOldWeights=True)
        self.prevValue["arrayWeights"] = oldArrayWeights

        # Get the existing blend weights, store them as previous
        prevBlendWeights = mFnSkinCluster.getBlendWeights(meshDagPath, importVertexCompObj)
        self.prevValue["arrayBlendWeights"] = prevBlendWeights
        # And set the new blend weights, if they were provided:
        if arrayBlendWeights:
            mFnSkinCluster.setBlendWeights(meshDagPath, importVertexCompObj, arrayBlendWeights)

#----------

def initializePlugin(plugin):
    """
    Plugin Bolierplate.
    Initialize the plug-in when loadPlugin is called.
    """
    # https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_1_1_m_fn_plugin_html
    pluginFn = om2.MFnPlugin(plugin, "www.akeric.com")
    try:
        pluginFn.registerCommand(SkinnerSetWeights.commandName,
                                 SkinnerSetWeights.cmdCreator,
                                 SkinnerSetWeights.createSyntax)
    except:
        om2.MGlobal.displayError("Failed to register command: %s\n"%SkinnerSetWeights.commandName)
        raise

def uninitializePlugin(plugin):
    """
    Plugin Bolierplate.
    Uninitialize the plug-in when the plugin is unloaded.

    """
    # https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__py_ref_class_open_maya_1_1_m_fn_plugin_html
    pluginFn = om2.MFnPlugin(plugin)
    try:
        pluginFn.deregisterCommand(SkinnerSetWeights.commandName)
    except:
        om2.MGlobal.displayError("Failed to unregister command: %s\n"%SkinnerSetWeights.commandName)
        raise
