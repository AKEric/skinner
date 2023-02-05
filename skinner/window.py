r"""
Name : skinner.window.py
Author : Eric Pavey - warpcat@gmail.com - https://github.com/AKEric/skinner
Creation Date : 2019-09-28
Description : Window / UI code for the skinner tool.  For the back-end API code,
    see skinner.core.py

    Dependencies:
    * Python 3.x+
    * numpy & scipy on the path for import. To install them for
        your version of Maya, see the skinner.core.py -> confirmDependencies function.
Updates:
    2021-09-26 : v1.0.0 : Ready for release.
    2021-10-01 : v1.0.1 : Bug fixing the 'Verbose Logging' checkbox not having
        its prefs stored.  Updating Window to have additional field for working
        with version control.
    2021-10-08 : v1.0.2 : Updating to expose 'Post Smooth Steps' field.  Other minor
        UI improvments.
    2021-10-19 : v1.0.3 : Adding notes about P4 usage in the Export tab.
    2021-10-21 : v1.0.4 : Setting 'Unbind First?' to True by default, to get around
        certain crashes when setting weights on 'old' skinClusters.
    2021-10-22 : v1.0.5 : Updating to add new import option that when a SkinChunk
        can't be found by mesh name, can if find one by matching vert count/order?
    2021-10-25 : v1.0.6 : Adding new section to print 'import overview' results.
        Adding new 'Export -> Set to bindpose?' checkbox.  Updating with link to
        the official docs!
    2021-11-01 : v1.0.7 : Updating with temp icon!
    2021-11-06 : v1.0.11 : Adding link to github page.
    2021-11-03 : v1.0.15 : Upating App.exportSkin to handle updates to core.exportSkin,
        core.exportTempSkin, and core.importTempSkin.
    2021-12-07 : v1.0.16 : Adding version info to SkinChunks, updating print code.
    2021-12-15 : v1.1.0 : Updating import tab to include new 'Import Using Pre-Deformed
        Shape Positions?'
    2021-12-19 : v1.1.1 : Updating enable/disable logic or 'Import Using Pre-Deformed
        Shape Positions?', 'Set To Bindpose?', and 'Unbind First?'.
    2021-12-30 : v1.1.2 : Updating all source to use Python3 type hint notation.
    2021-12-30 : v1.1.3 : Updating Window extras tab with separators and install path.
    2022-03-09 : v1.1.7 : Updating to add additional post-smoothing options.

Examples:

# Launch the window:
import skinner.window
skinner.window.App()
"""
import os
from functools import partial as callback

import maya.cmds as mc
import maya.api.OpenMaya as om2

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from PySide2 import QtWidgets, QtCore, QtGui

from . import core, utils

from . import __version__, __documentation__, __source__

#-----------------------


# PySide QSetting settings:
SETTING_LAST_SAVE_PATH = "setting_skinner_lastSavePath"
SETTING_LAST_TAB = "setting_skinner_lastTab"
SETTING_FALLBACK_SKIN_METHOD = "setting_skinner_fallbackSkinMethod"
SETTING_NUM_NEAREST_NEIGHBORS = "setting_skinner_numNearestNeighbors"
SETTING_NEARSET_NEIGHBOR_MULT = "setting_skinner_nearestNeighborMult"
SETTING_BUILD_MISSING_INFS = "setting_skinner_buildMissingInfs"
SETTING_FORCE_UBERCHUNK = "setting_skinner_forceUberChunk"
SETTING_UNBIND_FIRST = "setting_skinner_unbindFirst"
SETTING_SELECT_INSTEAD = "setting_skinner_selectInstead"
SETTING_VERBOSE_LOG = "setting_skinner_verboseLogging"
SETTING_MIN_PRINT_INDEX = "setting_skinner_minPrintIndex"
SETTING_MAX_PRINT_INDEX = "setting_skinner_maxPrintIndex"
SETTING_VERT_NORMAL_FILTER = "setting_skinner_vertNormalFilter"
SETTING_VERT_NORMAL_TOLLERANCE = "setting_skinner_vertNormalTollerance"
SETTING_VC_CALL = "setting_skinner_vcCall"
SETTING_DEPOT_ROOT = "setting_skinner_depotRoot"
SETTING_AUTO_FILL_DIR = "setting_skinner_autoFilldir"
SETTING_POST_SMOOTH_STEPS = "settings_skinner_postSmoothSteps"
SETTING_POST_DIFF_SMOOTH = "settings_skinner_postSmoothDiff"
SETTING_LOAD_BY_VERT_COUNT_NORMAL = "settings_skinner_loadByVertCountNormal"
SETTING_IMPORT_OVERVIEW = "settings_skinner_import_overview"
SETTINGS_IMPORT_USE_PRE_DEFORMED_SHAPE = "settings_skinner_importUsePreDeformedShape"
SETTING_IMPORT_SET_TO_BINDPOSE = "settings_skinner_importSetToBindpose"
SETTING_EXPORT_SET_TO_BINDPOSE = "settings_skinner_exportSetToBindpose"

#-----------------------
# UI Tools

def makeSeparator(mode="horizontal") -> QtWidgets.QFrame:
    """
    Make a QFrame designed to be a horizontal/vertical separator.

    Parameters:
    mode : string : Default "horizontal". Also supports "vertical".

    Return : QtWidgets.QFrame
    """
    wiget_separator = QtWidgets.QFrame()
    if mode == "horizontal":
        wiget_separator.setFrameStyle(QtWidgets.QFrame.HLine)
    elif mode == "vertical":
        wiget_separator.setFrameStyle(QtWidgets.QFrame.VLine)
    wiget_separator.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
    return wiget_separator

#-----------------------
# Window Code

class App(MayaQWidgetBaseMixin, QtWidgets.QWidget):
    """
    Interactive UI for the humans.
    """
    name = "skinnerWindow"
    title = 'Skinner'

    def __init__(self, vcExecCmd=None, vcDepotRoot=None, autoFillSubdir=None, docsOverride=__documentation__,
                 *args, **kwargs):
        """
        Init our main window.  There are certain defaults that you may want exposed
        to your team consistently:  That's what the below parameters are for.

        Parameters:
        vcExecCmd : string/None : Default None : Project level config:  If provided
            here, this value will be auto-filled into the Export tab's Version
            Control 'Exec Command' section and set i tto be read-only.  For
            details on what this string is, please see the docstring of
            skinner.core.py -> exportSkin.
        vcDepotRoot : string/None : Default None : Project level config:  If provided
            here, this value will be auto-filled into the Export tab's Version
            Control 'Depot Root' section, and set it to be read-only.  For
            details on what this string is, please see the docstring of
            skinner.core.py -> exportSkin.
        autoFillSubdir : string/None :  Default None : Project level config:  If
            provided here, this value will be auto-filled into the Extra tab's
            "'Auto-Fill' Subdir" field, and set it to be read-only.  This path is
            auto appended to the end of the dirname of the currently open file
            when the 'Auto-Fill' buttons are pressed, so that you can easily
            export weights to a standadized subdir structure.
        docsOverride : string/None : Default skinner.core.DOCS : Project level config:
            If overridden here, this is a web address to your own custom documentation
            for the tool that is launched by the 'Documentation...' button in
            the Extra's tab.  If this isn't provided, then the link in the
            skinner.core.DOCS global is used.
        """
        super(App, self).__init__(*args, **kwargs)

        if mc.window(App.name, exists=True):
            mc.deleteUI(App.name)

        self.vcExecCmd = vcExecCmd
        self.vcDepotRoot = vcDepotRoot
        self.autoFillSubdir = autoFillSubdir
        self.docsOverride = docsOverride

        self.setObjectName(App.name)
        self.setWindowTitle("%s : %s"%(App.title, __version__))
        self.setWindowFlags(QtCore.Qt.Window)
        self.setProperty("saveWindowPref", True) # Save prefs on exit.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.settings = QtCore.QSettings("AK_Eric", App.name)

        iconPath = utils.getIconPath()
        if iconPath:
            self.setWindowIcon(QtGui.QIcon(iconPath))

        self.nnOptions = []
        self.weightPaths = []
        self.widgets_printerCheckBoxes = []
        self.populate()
        # Reload the last place/side the window was in:
        try:
            self.restoreGeometry(self.settings.value("geometry", ""))
        except TypeError:
            pass
        self.show()
        # Filled out below

    def closeEvent(self, event:QtCore.QEvent):
        """
        Overridden supeclass method: Save any settings as we close the window.
        """
        # Save the last place/size the window was in:
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def hideEvent(self, event:QtCore.QEvent):
        """
        Delete the window instead of hiding it when presssing the 'X' button.
        """
        if not self.isMinimized():
            self.close()
            self.deleteLater()

    def populate(self):
        """
        Create the primary contents of our Window/Widget.
        """
        self.layout_main = QtWidgets.QVBoxLayout(self)
        if self.layout_main:
            self.widget_tab = QtWidgets.QTabWidget()
            self.layout_main.addWidget(self.widget_tab)
            if self.widget_tab:

                widget_importTab = QtWidgets.QWidget()
                widget_exportTab = QtWidgets.QWidget()
                widget_extrasTab = QtWidgets.QWidget()
                self.widget_tab.addTab(widget_importTab, "Import")
                self.widget_tab.addTab(widget_exportTab, "Export")
                self.widget_tab.addTab(widget_extrasTab, "Extras")

                tabIndex = self.settings.value(SETTING_LAST_TAB, 1)
                self.widget_tab.setCurrentIndex(tabIndex)
                self.widget_tab.currentChanged.connect(self.cbTabChanged)

                #---------------------------------------------------------------
                # IMPORT TAB
                layout_import = QtWidgets.QVBoxLayout()
                widget_importTab.setLayout(layout_import)
                if widget_importTab:
                    layout_importPath = QtWidgets.QHBoxLayout()
                    layout_import.addLayout(layout_importPath)
                    if layout_importPath:
                        layout_importPath.addWidget(QtWidgets.QLabel("Path:"))
                        self.widget_importPath = QtWidgets.QLineEdit()
                        self.widget_importPath.setReadOnly(True)
                        layout_importPath.addWidget(self.widget_importPath)

                        widget_autoFillImport = QtWidgets.QPushButton("<- Auto-Fill")
                        layout_importPath.addWidget(widget_autoFillImport)
                        widget_autoFillImport.setToolTip("Auto-fill the path based on the current scene name, and (optional) 'Auto-fill subdir' in the Extras tab.")
                        widget_autoFillImport.clicked.connect(self.cbAutoFillPath)

                        widget_importBrowser = QtWidgets.QPushButton("...")
                        widget_importBrowser.setToolTip("Browse to the skinner file to import.")
                        layout_importPath.addWidget(widget_importBrowser)
                        widget_importBrowser.clicked.connect(callback(self.cbFileBrowser, "import"))

                    layout_import.addWidget(makeSeparator())

                    layout_fbSkinMethod = QtWidgets.QHBoxLayout()
                    layout_import.addLayout(layout_fbSkinMethod)
                    if layout_fbSkinMethod:
                        widget_fallBackLabel = QtWidgets.QLabel("Fallback Skinning Method:")
                        layout_fbSkinMethod.addWidget(widget_fallBackLabel)
                        widget_fallBackLabel.setToolTip("For each mesh, if the vert count/order isn't 1:1, the algorithm to use to generate the new weights.")

                        self.widget_fallbackRadioGroup = QtWidgets.QButtonGroup()
                        widget_closestNeighbors = QtWidgets.QRadioButton("Closest Neighbors")
                        widget_closestNeighbors.setToolTip("Interpolate the weights of the closest imported vert neighbors, based on the below options.")
                        widget_closestPoint = QtWidgets.QRadioButton("Closest Point")
                        widget_closestPoint.setToolTip("Use the weights of the single closest imported vert position.")
                        self.widget_fallbackRadioGroup.addButton(widget_closestNeighbors, 1)
                        self.widget_fallbackRadioGroup.addButton(widget_closestPoint, 2)
                        layout_fbSkinMethod.addWidget(widget_closestNeighbors)
                        layout_fbSkinMethod.addWidget(widget_closestPoint)
                        fallbackMethod = self.settings.value(SETTING_FALLBACK_SKIN_METHOD, 1)
                        if fallbackMethod == 1:
                            widget_closestNeighbors.setChecked(True)
                        else:
                            widget_closestPoint.setChecked(True)

                        self.widget_fallbackRadioGroup.buttonClicked.connect(self.cbFallbackMethod)

                    layout_nnOptions = QtWidgets.QHBoxLayout()
                    layout_import.addLayout(layout_nnOptions)
                    if layout_nnOptions:
                        widget_nnOptionsLabel = QtWidgets.QLabel("Closest Neighbor Options:")
                        layout_nnOptions.addWidget(widget_nnOptionsLabel)
                        self.nnOptions.append(widget_nnOptionsLabel)
                        widget_nnOptionsLabel.setToolTip("Options used when the 'Fallback Skinning Method' is set to 'Closest Neighbors'")
                        layout_nnOptions.addStretch()

                        widget_numNearNeighborsLabel = QtWidgets.QLabel("Number Closest Neighbors:")
                        layout_nnOptions.addWidget(widget_numNearNeighborsLabel)
                        self.nnOptions.append(widget_numNearNeighborsLabel)
                        widget_numNearNeighborsLabel.setToolTip("Interpolate weights based on these number of neighbor verts, as long as they're within 'closest vert distance * nearest neighbor distance mult'. Zero or less means use all the neighbors found within that distance.")
                        self.widget_nearestNeighborNum = QtWidgets.QLineEdit()
                        nearNeighborValidator = QtGui.QIntValidator()
                        nearNeighborValidator.setBottom(0)
                        self.widget_nearestNeighborNum.setValidator(nearNeighborValidator)
                        nnVal = self.settings.value(SETTING_NUM_NEAREST_NEIGHBORS, 3)
                        self.widget_nearestNeighborNum.setText(str(nnVal))
                        layout_nnOptions.addWidget(self.widget_nearestNeighborNum)
                        self.widget_nearestNeighborNum.textChanged.connect(self.cbNearestNeighborOptions)
                        self.nnOptions.append(self.widget_nearestNeighborNum)
                        layout_nnOptions.addStretch()

                        widget_nearNeighborDistMultLabel = QtWidgets.QLabel("Nearest Neighbor Distance Mult:")
                        layout_nnOptions.addWidget(widget_nearNeighborDistMultLabel )
                        self.nnOptions.append(widget_nearNeighborDistMultLabel)
                        widget_nearNeighborDistMultLabel.setToolTip("Based on the distance to the closest target vert, what size radius (based on multiply by this value) around that should be searched for 'neigbor verts'?")
                        self.widget_nearestNeighborDistMult = QtWidgets.QLineEdit()
                        nearNeighborValidator = QtGui.QDoubleValidator()
                        nearNeighborValidator.setBottom(1.0)
                        self.widget_nearestNeighborDistMult.setValidator(nearNeighborValidator)
                        distMult = self.settings.value(SETTING_NEARSET_NEIGHBOR_MULT, 2.0)
                        self.widget_nearestNeighborDistMult.setText(str(float(distMult)))
                        layout_nnOptions.addWidget(self.widget_nearestNeighborDistMult)
                        self.widget_nearestNeighborDistMult.textChanged.connect(self.cbNearestNeighborOptions)
                        self.nnOptions.append(self.widget_nearestNeighborDistMult)

                    layout_import.addWidget(makeSeparator())

                    layout_vertNormal = QtWidgets.QHBoxLayout()
                    layout_import.addLayout(layout_vertNormal)
                    if layout_vertNormal:
                        tt_vertNormal = "Used to reduce 'stretching' source verts during import when there was overlapping mesh during export: If checked, target verts that don't have their normals within the tolerance to a source vert will be rejecetd."
                        self.widget_useVertNormal = QtWidgets.QCheckBox("Use Vert Normal Filter")
                        self.widget_useVertNormal.setToolTip(tt_vertNormal)
                        layout_vertNormal.addWidget(self.widget_useVertNormal)
                        if self.settings.value(SETTING_VERT_NORMAL_FILTER, 0):
                            self.widget_useVertNormal.setChecked(True)
                        self.widget_useVertNormal.clicked.connect(self.cbVertNormal)
                        layout_vertNormal.addStretch()
                        self.widget_vertNormalTolleranceLabel = QtWidgets.QLabel("Vert Normal Tolerance:")
                        self.widget_vertNormalTolleranceLabel.setToolTip(tt_vertNormal)
                        layout_vertNormal.addWidget(self.widget_vertNormalTolleranceLabel)
                        tolVal = self.settings.value(SETTING_VERT_NORMAL_TOLLERANCE, "0.75")
                        tolDefault = self.settings.value(SETTING_VERT_NORMAL_TOLLERANCE, tolVal)
                        self.widget_vertNormalTollerance = QtWidgets.QLineEdit(tolDefault)
                        self.widget_vertNormalTollerance.setToolTip(tt_vertNormal)
                        normalTolValid = QtGui.QDoubleValidator()
                        normalTolValid.setBottom(-1.0)
                        normalTolValid.setTop(1.0)
                        self.widget_vertNormalTollerance.setValidator(normalTolValid)
                        self.widget_vertNormalTollerance.editingFinished.connect(self.cbVertNormal)
                        layout_vertNormal.addWidget(self.widget_vertNormalTollerance)
                        if not self.settings.value(SETTING_VERT_NORMAL_FILTER, 0):
                            self.widget_vertNormalTollerance.setDisabled(True)
                            self.widget_vertNormalTolleranceLabel.setDisabled(True)

                        layout_vertNormal.addWidget(makeSeparator(mode="vertical"))

                        layout_vertNormal.addStretch()
                        tt_loadByVertCountOrder = "If a mesh can't find a SkinChunk name match, should it try to find one by vert count / order match? You generally want this checked on."
                        self.widget_loadByVeryCountOrderCheck = QtWidgets.QCheckBox("Load By Vert Count / Order?")
                        self.widget_loadByVeryCountOrderCheck.setToolTip(tt_loadByVertCountOrder)
                        if self.settings.value(SETTING_LOAD_BY_VERT_COUNT_NORMAL, True):
                            self.widget_loadByVeryCountOrderCheck.setChecked(True)
                        layout_vertNormal.addWidget(self.widget_loadByVeryCountOrderCheck)
                        self.widget_loadByVeryCountOrderCheck.clicked.connect(self.cbLoadVyVertcountOrder)


                    layout_moreOptions = QtWidgets.QGridLayout()
                    layout_import.addLayout(layout_moreOptions)
                    if layout_moreOptions:
                        self.widget_buildMissingInfs = QtWidgets.QCheckBox("Build Missing Influences?")
                        layout_moreOptions.addWidget(self.widget_buildMissingInfs, 0,0)
                        self.widget_buildMissingInfs.setToolTip("Build any missing joint influences this skinning counts on?  If any are missing, the skin import will fail.")
                        if self.settings.value(SETTING_BUILD_MISSING_INFS, True):
                            self.widget_buildMissingInfs.setChecked(True)
                        self.widget_buildMissingInfs.clicked.connect(self.cbMissingInfs)

                        self.widget_usePreDeformedShape = QtWidgets.QCheckBox("Import Using Pre-Deformed Shape Positions?")
                        layout_moreOptions.addWidget(self.widget_usePreDeformedShape, 0,1)
                        self.widget_usePreDeformedShape.setToolTip("If checked and a 'Fallback Skinning Method' is used during import, use the positions of the pre-deformed shape node (intermediateObject) for import, rather than the current (possibly deformed) worldspace locations.  This also uses the 'pre-deformed' worldspace positions in the SkinChunk. Usually you want this on.")
                        if self.settings.value(SETTINGS_IMPORT_USE_PRE_DEFORMED_SHAPE, True):
                            self.widget_usePreDeformedShape.setChecked(True)
                        self.widget_usePreDeformedShape.clicked.connect(self.cbImpoprtUsingPreDeformedShapePos)

                        self.widget_importSetBindpose = QtWidgets.QCheckBox("Set To Bindpose?")
                        layout_moreOptions.addWidget(self.widget_importSetBindpose, 0,2)
                        self.widget_importSetBindpose.setToolTip("Set all influences to their bindpose before exporring the new data?  Unnecessary if 'Import Using Pre-Deformed Shape' is checked. This happens before 'Unbind First'")
                        if self.settings.value(SETTING_IMPORT_SET_TO_BINDPOSE, False):
                            self.widget_importSetBindpose.setChecked(True)
                        self.widget_importSetBindpose.clicked.connect(self.cbImportSetToBindpose)

                        self.widget_unbindFirst = QtWidgets.QCheckBox("Unbind First?")
                        layout_moreOptions.addWidget(self.widget_unbindFirst, 0,3)
                        self.widget_unbindFirst.setToolTip("If any mesh is currently skinned, unbind it before import?  This will set the mesh back to the bindpose before skinning import. Otherwise the old/new skinning is merged together.  If you get crashes during load, setting this to True can help.")
                        if self.settings.value(SETTING_UNBIND_FIRST, True):
                            self.widget_unbindFirst.setChecked(True)
                        self.widget_unbindFirst.clicked.connect(self.cbUnbindFirst)

                        layout_moreOptions.addWidget(QtWidgets.QLabel("Debug Options:"), 1,0)

                        self.widget_forceUberChunk = QtWidgets.QCheckBox("Force Import From UberChunk?")
                        layout_moreOptions.addWidget(self.widget_forceUberChunk, 1,1)
                        self.widget_forceUberChunk.setToolTip("Force the weight import to use the point-cloud data in the UberChunk, instead of trying to find SkinChunk mesh name matches.")
                        if self.settings.value(SETTING_FORCE_UBERCHUNK, False):
                            self.widget_forceUberChunk.setChecked(True)
                        self.widget_forceUberChunk.clicked.connect(self.cbForceUberChunk)

                        self.widget_selectInstead = QtWidgets.QCheckBox("Select Instead Of Skin")
                        layout_moreOptions.addWidget(self.widget_selectInstead, 1,2)
                        self.widget_selectInstead.setToolTip("Instead of importing/applying the skinning, select the verts that will get skinning applied based on the loaded data.")
                        if self.settings.value(SETTING_SELECT_INSTEAD, False):
                            self.widget_selectInstead.setChecked(True)
                        self.widget_selectInstead.clicked.connect(self.cbSelInstead)

                    layout_postSmooth = QtWidgets.QHBoxLayout()
                    layout_import.addLayout(layout_postSmooth)
                    if layout_postSmooth:
                        tt_smooth = "If skin weights are loaded by any method than 1:1 vert order, should the tool apply any post-smoothing to make it look better?  It wil only smooth if the source mesh has more verts than the target SkinChunk."
                        widget_smoothLabel = QtWidgets.QLabel("Post-Skinning Smooth Options:")
                        layout_postSmooth.addWidget(widget_smoothLabel)
                        widget_smoothLabel.setToolTip(tt_smooth)

                        layout_postSmooth.addStretch()

                        tt_postSmoothSteps = "This is the number of iterations, set to 0 to disable. 2 is default."
                        widget_smoothLabel = QtWidgets.QLabel("Smooth Steps:")
                        layout_postSmooth.addWidget(widget_smoothLabel)
                        widget_smoothLabel.setToolTip(tt_postSmoothSteps)
                        self.widget_postSmooth = QtWidgets.QSpinBox()
                        layout_postSmooth.addWidget(self.widget_postSmooth)
                        self.widget_postSmooth.setMinimum(0)
                        postSmoothVal = self.settings.value(SETTING_POST_SMOOTH_STEPS, 2)
                        self.widget_postSmooth.setValue(postSmoothVal)
                        self.widget_postSmooth.setToolTip(tt_postSmoothSteps)
                        self.widget_postSmooth.valueChanged.connect(self.cbPostSmoothSteps)

                        layout_postSmooth.addStretch()

                        tt_postSmoothWeightDiff = "Weights will only be smoothed if their difference is GREATER than this value. Range from 0.01 -> 1.0, default 0.25 : *Smaller* values here will smooth *more* weights."
                        widget_postSmoothWeightDiffLabel = QtWidgets.QLabel("Weight Difference Threhold:")
                        layout_postSmooth.addWidget(widget_postSmoothWeightDiffLabel)
                        widget_postSmoothWeightDiffLabel.setToolTip(tt_postSmoothWeightDiff)

                        self.widget_postSmoothWeightDiff = QtWidgets.QLineEdit()
                        weightDiffValidator = QtGui.QDoubleValidator()
                        weightDiffValidator.setBottom(0.01)
                        weightDiffValidator.setTop(1.0)
                        self.widget_postSmoothWeightDiff.setToolTip(tt_postSmoothWeightDiff)
                        self.widget_postSmoothWeightDiff.setValidator(weightDiffValidator)
                        weightDiff = self.settings.value(SETTING_POST_DIFF_SMOOTH, 0.25)
                        self.widget_postSmoothWeightDiff.setText(str(float(weightDiff)))
                        layout_postSmooth.addWidget(self.widget_postSmoothWeightDiff)
                        self.widget_postSmoothWeightDiff.textChanged.connect(self.cbPostSmoothDiff)
                        #self.nnOptions.append(self.widget_postSmoothWeightDiff)
                        layout_postSmooth.addStretch()



                    layout_printOptions = QtWidgets.QHBoxLayout()
                    layout_import.addLayout(layout_printOptions)
                    if layout_printOptions:
                        widget_printReportLabel = QtWidgets.QLabel("Print Import Overview:")
                        layout_printOptions.addWidget(widget_printReportLabel)
                        widget_printReportLabel.setToolTip("Should an 'import overview' report be printed to the Script Editor?")
                        self.widget_importOvererviewGroup = QtWidgets.QButtonGroup()
                        widget_noOverview = QtWidgets.QRadioButton("None")
                        widget_noOverview.setToolTip("Print no report")
                        widget_overviewByType = QtWidgets.QRadioButton("By Import Type")
                        widget_overviewByType.setToolTip("Organize the report based on import type.")
                        widget_overviewByMesh = QtWidgets.QRadioButton("By Mesh Name")
                        widget_overviewByMesh.setToolTip("Organize the report based on mesh name.")
                        self.widget_importOvererviewGroup.addButton(widget_noOverview, 1)
                        self.widget_importOvererviewGroup.addButton(widget_overviewByType, 2)
                        self.widget_importOvererviewGroup.addButton(widget_overviewByMesh, 3)
                        for widget in (widget_noOverview, widget_overviewByType, widget_overviewByMesh):
                            layout_printOptions.addWidget(widget)
                        overviewType = self.settings.value(SETTING_IMPORT_OVERVIEW, 2)
                        if overviewType == 1:
                            widget_noOverview.setChecked(True)
                        elif overviewType == 2:
                            widget_overviewByType.setChecked(True)
                        elif overviewType == 3:
                            widget_overviewByMesh.setChecked(True)
                        self.widget_importOvererviewGroup.buttonClicked.connect(self.cbImportOverview)

                    layout_import.addWidget(makeSeparator())

                    layout_importButs = QtWidgets.QGridLayout()
                    layout_import.addLayout(layout_importButs)
                    if layout_importButs:
                        widget_import = QtWidgets.QPushButton("Import From Path")
                        layout_importButs.addWidget(widget_import,0,0)
                        widget_import.setToolTip("Import skinner weights on the selected mesh hierarchy.")
                        widget_import.clicked.connect(callback(self.importSkin, "browser"))

                        widget_importTemp = QtWidgets.QPushButton("Import Temp")
                        layout_importButs.addWidget(widget_importTemp,0,1)
                        widget_importTemp.setToolTip("Import skinner weights on the selected mesh hierarchy, from the last exported temp file.")
                        widget_importTemp.clicked.connect(callback(self.importSkin, mode='temp'))

                    layout_import.addStretch()

                #---------------------------------------------------------------
                # EXPORT TAB
                layout_export = QtWidgets.QVBoxLayout()
                widget_exportTab.setLayout(layout_export)
                if layout_export:
                    layout_exportPath = QtWidgets.QHBoxLayout()
                    layout_export.addLayout(layout_exportPath)
                    if layout_exportPath:
                        layout_exportPath.addWidget(QtWidgets.QLabel("Path:"))
                        self.widget_exportPath = QtWidgets.QLineEdit()
                        self.widget_exportPath.setReadOnly(True)
                        layout_exportPath.addWidget(self.widget_exportPath)

                        widget_autoFillExport = QtWidgets.QPushButton("<- Auto-Fill")
                        layout_exportPath.addWidget(widget_autoFillExport)
                        widget_autoFillExport.setToolTip("Auto-fill the path based on the current scene name, and (optional) 'Auto-fill subdir' in the Extras tab.")
                        widget_autoFillExport.clicked.connect(self.cbAutoFillPath)

                        widget_exportBrowser = QtWidgets.QPushButton("...")
                        widget_exportBrowser.setToolTip("Browse to the skinner file to export.")
                        layout_exportPath.addWidget(widget_exportBrowser)
                        widget_exportBrowser.clicked.connect(callback(self.cbFileBrowser, "export"))

                    layout_exportButs = QtWidgets.QGridLayout()
                    layout_export.addLayout(layout_exportButs)
                    if layout_exportButs:

                        self.widget_exportSetBindpose = QtWidgets.QCheckBox("Set To Bindpose?")
                        self.widget_exportSetBindpose.setToolTip("If checked, set all influence to their bindpose before exporting the Skinner weights. Good to have checked so as to store out the bindpose transforms for the joints, so they can be rebuilt correctly during import.  But not needed if that isn't a concern.")
                        layout_exportButs.addWidget(self.widget_exportSetBindpose,0,0)
                        if self.settings.value(SETTING_EXPORT_SET_TO_BINDPOSE, True):
                            self.widget_exportSetBindpose.setChecked(True)
                        self.widget_exportSetBindpose.clicked.connect(self.cbExportSetToBindpose)

                        widget_export = QtWidgets.QPushButton("Export To Path")
                        layout_exportButs.addWidget(widget_export,1,0)
                        widget_export.setToolTip("Export skinner weights on the selected mesh hierarchy, based on the above path.")
                        widget_export.clicked.connect(callback(self.exportSkin, mode='browser'))

                        widget_exportTemp = QtWidgets.QPushButton("Export Temp")
                        layout_exportButs.addWidget(widget_exportTemp,1,1)
                        widget_exportTemp.setToolTip("Export skinner weights on the selected mesh hierarchy, to a temp file.")
                        widget_exportTemp.clicked.connect(callback(self.exportSkin, mode='temp'))

                    layout_export.addWidget(makeSeparator())

                    layout_export.addWidget(QtWidgets.QLabel("Version Control:"))
                    layout_vcExecCmd = QtWidgets.QHBoxLayout()
                    layout_export.addLayout(layout_vcExecCmd)
                    if layout_vcExecCmd:
                        layout_vcExecCmd.addWidget(QtWidgets.QLabel("Exec Command:"))
                        vcCmd = None
                        if self.vcExecCmd:
                            vcCmd = self.vcExecCmd
                        else:
                            vcCmd = self.settings.value(SETTING_VC_CALL, "")
                        self.widget_vcCmd = QtWidgets.QLineEdit(vcCmd)
                        self.widget_vcCmd.editingFinished.connect(self.cbVcCmd)
                        layout_vcExecCmd.addWidget(self.widget_vcCmd)
                        self.widget_vcCmd.setToolTip("Enter the command that should be executed to add/edit the exported file to your version control: It must include a string formatted \"'%s'\" in it, to string-format in the filepath. You can separte multiple calls by ending them with a semicolon ;")
                        if self.vcExecCmd:
                            self.widget_vcCmd.setEnabled(False)
                    layout_vcDepotRoot = QtWidgets.QHBoxLayout()
                    layout_export.addLayout(layout_vcDepotRoot)
                    if layout_vcDepotRoot:
                        layout_vcDepotRoot.addWidget(QtWidgets.QLabel("Depot Root:"))
                        depotRoot = None
                        if self.vcDepotRoot:
                            depotRoot = self.vcDepotRoot
                        else:
                            depotRoot = self.settings.value(SETTING_DEPOT_ROOT, "")
                        self.widget_depotRoot = QtWidgets.QLineEdit(depotRoot)
                        self.widget_depotRoot.setReadOnly(True)
                        layout_vcDepotRoot.addWidget(self.widget_depotRoot)
                        self.widget_depotRoot.setToolTip("Only files living under this directory will be added to your version control. Leaving this empty will disable version control. To clear it, open the browser, and then cancel.")
                        if self.vcDepotRoot:
                            self.widget_depotRoot.setEnabled(False)

                        widget_depotBrowser = QtWidgets.QPushButton("...")
                        widget_depotBrowser.clicked.connect(self.cbDepotRoot)
                        layout_vcDepotRoot.addWidget(widget_depotBrowser)
                    layout_export.addWidget(QtWidgets.QLabel(f"IMPORTANT: If you're using P4 for version control, be sure to set its '.{core.EXT}' file type to 'binary', or it will mangle them on the server."))
                    layout_export.addWidget(QtWidgets.QLabel("See its 'p4 typemap' command."))

                    layout_export.addStretch()

                #---------------------------------------------------------------
                # EXTRAS TAB

                layout_extras = QtWidgets.QVBoxLayout()
                widget_extrasTab.setLayout(layout_extras)
                if layout_extras:
                    layout_extrasGrid = QtWidgets.QGridLayout()
                    layout_extras.addLayout(layout_extrasGrid)
                    if layout_extrasGrid:
                        widget_runTest = QtWidgets.QPushButton("Run the 'skinner test suite'?")
                        layout_extrasGrid.addWidget(widget_runTest, 0,0)
                        widget_runTest.setToolTip("This will prompt the user to create a new empty scene, and run a series of tests: The results will be printed to the Script Editor")
                        widget_runTest.clicked.connect(core.test)

                        layout_docs = QtWidgets.QHBoxLayout()
                        layout_extrasGrid.addLayout(layout_docs, 0, 1)
                        if layout_docs:

                            widget_homepage = QtWidgets.QPushButton("Homepage...")
                            layout_docs.addWidget(widget_homepage)
                            widget_homepage.clicked.connect(self.cbOpenHomepage)

                            widget_docs = QtWidgets.QPushButton("Documentation...")
                            layout_docs.addWidget(widget_docs)
                            widget_docs.clicked.connect(self.cbShowDocs)

                        self.widget_verboseLogging = QtWidgets.QCheckBox("Verbose Logging?")
                        layout_extrasGrid.addWidget(self.widget_verboseLogging, 1,0)
                        self.widget_verboseLogging.setToolTip("Print verbose results of the import/export operations to the Maya Script Editor?  If this is unchecked, nothing (unless errors) will be printed to the Script Editor.")
                        if self.settings.value(SETTING_VERBOSE_LOG, True):
                            self.widget_verboseLogging.setChecked(True)
                        self.widget_verboseLogging.clicked.connect(self.cbVerboseLog)

                        layout_autoFill = QtWidgets.QHBoxLayout()
                        layout_extrasGrid.addLayout(layout_autoFill, 1,1)
                        if layout_autoFill:
                            layout_autoFill.addWidget(QtWidgets.QLabel("'Auto-Fill' Subdir:"))
                            autoFillDir = None
                            if self.autoFillSubdir:
                                autoFillDir = self.autoFillSubdir
                            else:
                                autoFillDir = self.settings.value(SETTING_AUTO_FILL_DIR, "")
                            self.widget_autoFillDir = QtWidgets.QLineEdit(autoFillDir)
                            self.widget_autoFillDir.setToolTip("If provided (optional), this is some subdir of the currently open scene where the '<- Auto-Fill' tools will update the paths to.")
                            self.widget_autoFillDir.editingFinished.connect(self.cbAutoFillSubdir)
                            layout_autoFill.addWidget(self.widget_autoFillDir)
                            if self.autoFillSubdir:
                                self.widget_autoFillDir.setEnabled(False)

                        packageDir = os.path.dirname(__file__)
                        layout_extrasGrid.addWidget(QtWidgets.QLabel(f"Package Path:"), 2,0, QtCore.Qt.AlignRight)
                        widget_packagePath = QtWidgets.QLineEdit(packageDir)
                        widget_packagePath.setReadOnly(True)
                        layout_extrasGrid.addWidget(widget_packagePath, 2,1)

                        # ----------
                        # sknr / SkinChunk Printing:

                        # Visually separate the below section from above
                        layout_extrasGrid.addWidget(makeSeparator(), 3, 0)
                        layout_extrasGrid.addWidget(makeSeparator(), 3, 1)

                        layout_extrasGrid.addWidget(QtWidgets.QLabel(f"Print .{core.EXT} File Info"), 4,0)
                        widget_printButs = QtWidgets.QWidget()
                        layout_extrasGrid.addWidget(widget_printButs, 5,0)
                        layout_printButs = QtWidgets.QGridLayout()
                        widget_printButs.setLayout(layout_printButs)
                        if layout_printButs:
                            #layout_printButs.addWidget(QtWidgets.QLabel("Print %s file info..."%core.EXT))
                            widget_printSknr = QtWidgets.QPushButton("Browse and print...")
                            layout_printButs.addWidget(widget_printSknr,0,0)
                            widget_printSknr.setToolTip("Browse to a .%s file on disk, and print info on it to the Script Editor, based on what's checked."%core.EXT)
                            widget_printSknr.clicked.connect(self.printSkinInfo)

                            widget_minMaxIndices = QtWidgets.QWidget()

                            layout_printButs.addWidget(widget_minMaxIndices, 0, 1)
                            if widget_minMaxIndices:
                                tt_minMaxIndices = "There could be a lot of stuff to print:  Here, you can control the range of vert index info that is printed.  Min 0 starts at the beginning.  Max 0 prints until the end. Max supports negative indices "
                                layout_minMaxIndices = QtWidgets.QHBoxLayout()
                                widget_minMaxIndices.setLayout(layout_minMaxIndices)
                                label_minMaxIndices = QtWidgets.QLabel("Min/Max Print Indices:")
                                layout_minMaxIndices.addWidget(label_minMaxIndices)
                                minVal = self.settings.value(SETTING_MIN_PRINT_INDEX, "0")
                                maxVal = self.settings.value(SETTING_MAX_PRINT_INDEX, "0")
                                self.widget_minPrintIndex = QtWidgets.QLineEdit(minVal)
                                self.widget_maxPrintIndex = QtWidgets.QLineEdit(maxVal)
                                layout_minMaxIndices.addWidget(self.widget_minPrintIndex)
                                layout_minMaxIndices.addWidget(self.widget_maxPrintIndex)
                                intValidator = QtGui.QIntValidator()
                                self.widget_minPrintIndex.setValidator(intValidator)
                                self.widget_maxPrintIndex.setValidator(intValidator)
                                for widget in (widget_minMaxIndices, self.widget_minPrintIndex, self.widget_maxPrintIndex):
                                    widget.setToolTip(tt_minMaxIndices)

                                self.widget_minPrintIndex.editingFinished.connect(self.cbMinMaxPrintIndinces)
                                self.widget_maxPrintIndex.editingFinished.connect(self.cbMinMaxPrintIndinces)

                            widget_checkAll = QtWidgets.QPushButton("Check All")
                            layout_printButs.addWidget(widget_checkAll, 1,0)
                            widget_checkAll.clicked.connect(callback(self.cbCheckPrintOptions, True))

                            widget_checkNone = QtWidgets.QPushButton("Check None")
                            layout_printButs.addWidget(widget_checkNone, 1,1)
                            widget_checkNone.clicked.connect(callback(self.cbCheckPrintOptions, False))

                            layout_printButs.setRowStretch(2,1)


                        wiget_printOptions = QtWidgets.QWidget()
                        layout_extrasGrid.addWidget(wiget_printOptions, 5,1)
                        layout_printOptions = QtWidgets.QGridLayout()
                        wiget_printOptions.setLayout(layout_printOptions)
                        if layout_printOptions:
                            row = 0
                            column = 0
                            maxCol = 3
                            # These are the same as the arg names to SkinChunk.printData:
                            # they should be kept in sync.
                            buttons = ["version","meshShape", "creationDate",
                                       "importPath", "user", "skinMethod", "meshVertCount",
                                       "numVerts", "vertIds", "infNum", "influences",
                                       "hasPreDeformedData", "atBindPose",
                                       "blendWeightsPerVert","infWeightsPerVert", "normalsPerVert", "neighbors" ]
                            for i,but in enumerate(buttons):
                                if i%maxCol == 0 and i != 0:
                                    row = 0
                                    column += 1
                                widget_printBut = QtWidgets.QCheckBox(but)
                                layout_printOptions.addWidget(widget_printBut, column, row )
                                widget_printBut.setChecked(True)
                                self.widgets_printerCheckBoxes.append(widget_printBut)
                                row += 1

                        layout_extrasGrid.setRowStretch(5,1)

                layout_extras.addStretch()

        # Update our options enabled state:
        checkedButton = self.widget_fallbackRadioGroup.checkedButton()
        if checkedButton.text() == "Closest Neighbors":
            self.settings.setValue(SETTING_FALLBACK_SKIN_METHOD, 1)
            for wid in self.nnOptions:
                wid.setDisabled(False)
        else:
            self.settings.setValue(SETTING_FALLBACK_SKIN_METHOD, 2)
            for wid in self.nnOptions:
                wid.setDisabled(True)

    #------------------
    # Callbacks

    def cbTabChanged(self, *args):
        """
        Callback excuted when the tab is changed, to save the last tab int value.
        """
        self.settings.setValue(SETTING_LAST_TAB, args[0])

    def cbFileBrowser(self, mode:str):
        """
        Callback for importing/exporing skinner files.  Updates the UI.
        Note, during impor the user could choose multiple files.

        Parameters:
        mode : string : Supports "import" and "export".
        """
        ok = ""
        fileMode = None
        fileStr = ""
        if mode == "export":
            fileMode = 0
            ok = "Export"
            fileStr = "File"
        elif mode == "import":
            fileMode = 4 # one or more existing files
            ok = "Import"
            fileStr = "File(s)"
        else:
            raise Exception("mode '%s' is invalid"%mode)

        startDir = self.settings.value(SETTING_LAST_SAVE_PATH, "")
        weightPaths = mc.fileDialog2(caption="Choose Skin %s"%fileStr, fileMode=fileMode, okCaption=ok,
                                     fileFilter="Skinner Files: (*.%s)"%core.EXT, startingDirectory=startDir)

        if weightPaths:
            weightDir = os.path.dirname(weightPaths[0].replace("/", "\\"))
            self.settings.setValue(SETTING_LAST_SAVE_PATH, weightDir)
            self.weightPaths = weightPaths

            if mode == "import":
                if len(weightPaths) == 1:
                    self.widget_exportPath.setText(weightPaths[0])
                    self.widget_importPath.setText(weightPaths[0])
                else:
                    self.widget_exportPath.setText("")
                    self.widget_importPath.setText("< Multiple (%s) >"%len(weightPaths))

            if mode == "export":
                filePath = weightPaths[0].replace("/", "\\")
                self.widget_exportPath.setText(filePath)
                self.widget_importPath.setText(filePath)
                if os.path.isfile(filePath):
                    if not os.access(filePath, os.W_OK):
                        errStr = "The provided weight file is read-only: Please make it writable before exporting:"
                        om2.MGlobal.displayError("skinner : %s %s"%(errStr, filePath))
                        mc.confirmDialog(title="Skinner Error",
                                         message="%s\n%s"%(errStr, filePath),
                                         button="Ok")
        else:
            self.weightPaths = []
            self.widget_exportPath.setText("")
            self.widget_importPath.setText("")

    def cbAutoFillPath(self):
        """
        Auto-fill both the import & export paths based on the current scene name,
        including anything entered into the'Auto-Fill Subdir' in the Extras tab.
        """
        sceneName = mc.file(query=True, sceneName=True)
        if not sceneName:
            om2.MGlobal.displayWarning("The current Maya file isn't saved:  Can't 'Auto-Fill' the paths.")
            return

        dirName, fileNameExt = os.path.split(sceneName)
        fileName = os.path.splitext(fileNameExt)[0]
        exportDir = dirName
        subdir = self.widget_autoFillDir.text().strip()
        if subdir:
            for slash in ("\\", "/"):
                if subdir.startswith(slash):
                    subdir = subdir[1:]
                if subdir.endswith(slash):
                    subdir = subdir[:-1]
            exportDir = os.path.join(dirName, subdir)
        pathname = os.path.normpath(os.path.join(exportDir, f"{fileName}.{core.EXT}"))

        self.widget_importPath.setText(pathname)
        self.widget_exportPath.setText(pathname)
        self.settings.setValue(SETTING_LAST_SAVE_PATH, exportDir)
        self.weightPaths = [pathname]

    def cbFallbackMethod(self, *args):
        """
        The callback executed when the 'Fallback Skinning Method' radio button is
        clicked.
        """
        radioButton = args[0]
        if radioButton.text() == "Closest Neighbors":
            self.settings.setValue(SETTING_FALLBACK_SKIN_METHOD, 1)
            for wid in self.nnOptions:
                wid.setDisabled(False)
        elif radioButton.text() == "Closest Point":
            self.settings.setValue(SETTING_FALLBACK_SKIN_METHOD, 2)
            for wid in self.nnOptions:
                wid.setDisabled(True)

    def cbNearestNeighborOptions(self):
        """
        The callback executed when a 'Nearest Neighbor Option' value is changed,
        to save the prefs
        """
        nnn = float(self.widget_nearestNeighborNum.text())
        self.settings.setValue(SETTING_NUM_NEAREST_NEIGHBORS, nnn)
        distMult = float(self.widget_nearestNeighborDistMult.text())
        self.settings.setValue(SETTING_NEARSET_NEIGHBOR_MULT, distMult)

    def cbMissingInfs(self):
        """
        Callback executed to save the state of the 'Build Missing Influences?'
        checkbox.
        """
        if self.widget_buildMissingInfs.checkState():
            self.settings.setValue(SETTING_BUILD_MISSING_INFS, 1)
        else:
            self.settings.setValue(SETTING_BUILD_MISSING_INFS, 0)

    def cbForceUberChunk(self):
        """
        Callback executed to save the state of the 'Force Import From UberChunk?'
        checkbox.
        """
        if self.widget_forceUberChunk.checkState():
            self.settings.setValue(SETTING_FORCE_UBERCHUNK, 1)
        else:
            self.settings.setValue(SETTING_FORCE_UBERCHUNK, 0)



    def cbSelInstead(self):
        """
        Callback executed to save the state of the 'Select instead of skin' checkbox.
        """
        if self.widget_selectInstead.checkState():
            self.settings.setValue(SETTING_SELECT_INSTEAD, 1)
        else:
            self.settings.setValue(SETTING_SELECT_INSTEAD, 0)

    def cbVerboseLog(self):
        """
        Callback executed to save the state of the 'Verbose Logging?'checkbox.
        """
        if self.widget_verboseLogging.checkState():
            self.settings.setValue(SETTING_VERBOSE_LOG, 1)
        else:
            self.settings.setValue(SETTING_VERBOSE_LOG, 0)

    def cbCheckPrintOptions(self, mode:int):
        """
        Callback executed from the 'Check All' or 'Check None' buttons, to set
        those checkbox states.
        """
        for widget in self.widgets_printerCheckBoxes:
            widget.setChecked(mode)

    def cbMinMaxPrintIndinces(self):
        """
        Callback executed to save the prefs of the 'min max print indices' section.
        """
        minVal = self.widget_minPrintIndex.text()
        maxVal = self.widget_maxPrintIndex.text()
        self.settings.setValue(SETTING_MIN_PRINT_INDEX, minVal)
        self.settings.setValue(SETTING_MAX_PRINT_INDEX, maxVal)

    def cbVertNormal(self):
        """
        Save the prefs of the vert normal filter checkbox and tolerance.
        Also enable/disable the vert normal UI elements.
        """
        userVertNormal = 1 if self.widget_useVertNormal.isChecked() else 0
        vertNormalTolerance = self.widget_vertNormalTollerance.text()
        self.settings.setValue(SETTING_VERT_NORMAL_FILTER, userVertNormal)
        self.settings.setValue(SETTING_VERT_NORMAL_TOLLERANCE, vertNormalTolerance)
        if userVertNormal:
            self.widget_vertNormalTollerance.setDisabled(False)
            self.widget_vertNormalTolleranceLabel.setDisabled(False)
        else:
            self.widget_vertNormalTollerance.setDisabled(True)
            self.widget_vertNormalTolleranceLabel.setDisabled(True)

    def cbVcCmd(self):
        """
        Save the pref for the 'version control command'.
        """
        vcCmd = self.widget_vcCmd.text().strip()
        self.settings.setValue(SETTING_VC_CALL, vcCmd)

    def cbDepotRoot(self):
        """
        Browse to the depot root, and save the pref for the 'depot root' path.
        """
        startDir = self.settings.value(SETTING_DEPOT_ROOT, "")
        depotRoot = mc.fileDialog2(caption="Select Version Control Depot Root Dir", fileMode=2,
                                   startingDirectory=startDir, okCaption="Select")
        if not depotRoot:
            self.widget_depotRoot.setText("")
            self.settings.setValue(SETTING_DEPOT_ROOT, "")
            return
        depotRoot = depotRoot[0]
        self.widget_depotRoot.setText(depotRoot)
        self.settings.setValue(SETTING_DEPOT_ROOT, depotRoot)

    def cbAutoFillSubdir(self):
        """
        Callback to store the directory name that will be auto-added to the 'auto
        fill' tool
        """
        autoFillDir = self.widget_autoFillDir.text().strip()
        self.settings.setValue(SETTING_AUTO_FILL_DIR, autoFillDir)

    def cbShowDocs(self):
        """
        Open the documentation web link.  Could be an override to custom docs.
        """
        if not self.docsOverride:
            om2.MGlobal.displayWarning("Sorry, no docs are avilable")
            return
        mc.showHelp(self.docsOverride, absolute=True)

    def cbOpenHomepage(self):
        """
        Open the github source link
        """
        mc.showHelp(__source__, absolute=True)

    def cbPostSmoothSteps(self):
        """
        Callback executed to store the 'post smooth steps' value.
        """
        postSmoothSteps = self.widget_postSmooth.value()
        self.settings.setValue(SETTING_POST_SMOOTH_STEPS, postSmoothSteps)

    def cbPostSmoothDiff(self):
        """
        The callback executed when the 'Weight Different Threhold' value is changed,
        to save the prefs
        """
        pswd = float(self.widget_postSmoothWeightDiff.text())
        self.settings.setValue(SETTING_POST_DIFF_SMOOTH, pswd)

    def cbLoadVyVertcountOrder(self):
        """
        Callback executed to store the 'Load By Vert Count / Order' value.
        """
        if self.widget_loadByVeryCountOrderCheck.isChecked():
            self.settings.setValue(SETTING_LOAD_BY_VERT_COUNT_NORMAL, 1)
        else:
            self.settings.setValue(SETTING_LOAD_BY_VERT_COUNT_NORMAL, 0)

    def cbImportOverview(self, *args):
        """
        The callback executed when the 'Import Overview Type' radio button is
        clicked.
        """
        radioButton = args[0]
        if radioButton.text() == "None":
            self.settings.setValue(SETTING_IMPORT_OVERVIEW, 1)
        elif radioButton.text() == "By Import Type":
            self.settings.setValue(SETTING_IMPORT_OVERVIEW, 2)
        elif radioButton.text() == "By Mesh Name":
            self.settings.setValue(SETTING_IMPORT_OVERVIEW, 3)

    def cbExportSetToBindpose(self):
        """
        Callback executed to save the state of the 'Set To Bindpose?' checkbox in the
        export tab.
        """
        if self.widget_exportSetBindpose.checkState():
            self.settings.setValue(SETTING_EXPORT_SET_TO_BINDPOSE, 1)
        else:
            self.settings.setValue(SETTING_EXPORT_SET_TO_BINDPOSE, 0)


    def cbImpoprtUsingPreDeformedShapePos(self):
        """
        Callback executed to save the state of the 'Import Using Pre-Deformed Shape
        Positions?' checkbox in the import tab.  It also unchecks 'Set To Bindpose'
        and 'Unbind First'.
        """
        if self.widget_usePreDeformedShape.checkState():
            self.settings.setValue(SETTINGS_IMPORT_USE_PRE_DEFORMED_SHAPE, 1)

            self.widget_importSetBindpose.setChecked(False)
            self.widget_unbindFirst.setChecked(False)
            self.settings.setValue(SETTING_IMPORT_SET_TO_BINDPOSE, 0)
            self.settings.setValue(SETTING_UNBIND_FIRST, 0)
        else:
            self.settings.setValue(SETTINGS_IMPORT_USE_PRE_DEFORMED_SHAPE, 0)

    def cbImportSetToBindpose(self):
        """
        Callback executed to save the state of the 'Set To Bindpose?' checkbox in the
        import tab.  This also unchecks 'Import Using Pre-Deformed Shape Positions?'.
        """
        if self.widget_importSetBindpose.checkState():
            self.settings.setValue(SETTING_IMPORT_SET_TO_BINDPOSE, 1)

            self.widget_usePreDeformedShape.setChecked(False)
            self.settings.setValue(SETTINGS_IMPORT_USE_PRE_DEFORMED_SHAPE, 0)
        else:
            self.settings.setValue(SETTING_IMPORT_SET_TO_BINDPOSE, 0)

    def cbUnbindFirst(self):
        """
        Callback executed to save the state of the 'Unbind First?' checkbox.
        It also unchecks 'Import Using Pre-Deformed Shape Positions?' and enables
        'Set To Bindpose'.
        """
        if self.widget_unbindFirst.checkState():
            self.settings.setValue(SETTING_UNBIND_FIRST, 1)

            self.widget_importSetBindpose.setChecked(True)
            self.widget_usePreDeformedShape.setChecked(False)

            self.settings.setValue(SETTING_IMPORT_SET_TO_BINDPOSE, 1)
            self.settings.setValue(SETTINGS_IMPORT_USE_PRE_DEFORMED_SHAPE, 0)
        else:
            self.settings.setValue(SETTING_UNBIND_FIRST, 0)

    #------------------
    # Actions

    def printSkinInfo(self):
        """
        Browse to, and print the values for the provided sknr file.
        """
        startDir = self.settings.value(SETTING_LAST_SAVE_PATH, "")
        filePaths = mc.fileDialog2(caption="Choose Skin File(s)", fileMode=4, okCaption="Print!",
                                   fileFilter="Skinner Files: (*.%s)"%core.EXT, startingDirectory=startDir)
        if not filePaths:
            return

        printArgs = {}
        for checkbox in self.widgets_printerCheckBoxes:
            text = checkbox.text()
            checked = int(checkbox.checkState())
            if checked:
                printArgs[text] = True
            else:
                printArgs[text] = False
        infListSlice = [int(self.widget_minPrintIndex.text()), int(self.widget_maxPrintIndex.text())]
        printArgs["infListSlice"] = infListSlice

        skinChunks = core.importSkinChunks(filePaths, verbose=False)
        for skinChunk in skinChunks:
            skinChunk.printData(**printArgs)

    def importSkin(self, mode="browser"):
        """
        When the 'Import' button is pressed.

        Parameters:
        mode : string : Default "browser".  Also supports "temp".
        """
        if  mode not in ("browser", "temp"):
            raise Exception("Invalid 'mode' arg provided: %s"%mode)

        try:
            utils.getMeshVertIds()
        except AssertionError:
            om2.MGlobal.displayError("No mesh is selected to import skin weights on.")
            return

        paths = None
        if mode == "browser":
            if not self.weightPaths:
                self.cbFileBrowser("import")
                if not self.weightPaths:
                    om2.MGlobal.displayInfo("Exiting export: No path choosen.")
                    return
            paths = self.weightPaths
        elif mode == "temp":
            if os.path.isfile(core.TEMP_FILE_PATH):
                paths = [core.TEMP_FILE_PATH]
            else:
                om2.MGlobal.displayError("No 'temp skinner file' on disk:  Please 'Export -> Export Temp' first.")
                return

        missing = []
        for path in paths:
            if not os.path.isfile(path):
                missing.append(path)
        if missing:
            print("Missing skinner files:")
            for mis in missing:
                print("    %s"%mis)
            om2.MGlobal.displayError("Missing the above %s Skinner files for import ^^"%(len(missing)))
            return

        fallbackSkinningMethod = ""
        uiFallbackSkinMethod = self.widget_fallbackRadioGroup.checkedButton().text()
        if uiFallbackSkinMethod == "Closest Neighbors":
            fallbackSkinningMethod = "closestNeighbors"
        elif uiFallbackSkinMethod == "Closest Point":
            fallbackSkinningMethod = "closestPoint"
        buildMissingInfs = True if int(self.widget_buildMissingInfs.checkState()) else False
        setToBindpose = self.widget_importSetBindpose.isChecked()
        forceUberChunk = True if int(self.widget_forceUberChunk.checkState()) else False
        importUsingPreDeformedPoints = True if int(self.widget_usePreDeformedShape.checkState()) else False
        unbindFirst = True if int(self.widget_unbindFirst.checkState()) else False
        selInsteadOfSkin = True if int(self.widget_selectInstead.checkState()) else False
        verbose = True if int(self.widget_verboseLogging.checkState()) else False  #!!! NEED TO FIX
        printOverview = False
        printOverviewMode = "byImportType"
        checkedButWidget = self.widget_importOvererviewGroup.checkedButton()
        importOverviewText = checkedButWidget.text()
        if importOverviewText == "By Import Type":
            printOverview = True
            printOverviewMode = "byImportType"
        elif importOverviewText == "By Mesh Name":
            printOverview = True
            printOverviewMode = "byMesh"

        filterByVertNormal = True if self.widget_useVertNormal.isChecked() else False
        vertNormalTolerance = float(self.widget_vertNormalTollerance.text())
        postSmoothSteps = self.widget_postSmooth.value()
        postSmoothWeightDiff = float(self.widget_postSmoothWeightDiff.text())

        closestNeighborCount = int(self.widget_nearestNeighborNum.text())
        closestNeighborDistMult = float(self.widget_nearestNeighborDistMult.text())

        mc.undoInfo(openChunk=True)

        result = core.importSkin(items=None, filePaths=paths, verbose=verbose,
                                 printOverview=printOverview, printOverviewMode=printOverviewMode,
                                 # kwargs passed to setWeights
                                 fallbackSkinningMethod=fallbackSkinningMethod,
                                 closestNeighborCount=closestNeighborCount,
                                 closestNeighborDistMult=closestNeighborDistMult,
                                 filterByVertNormal=filterByVertNormal,
                                 vertNormalTolerance=vertNormalTolerance,
                                 createMissingInfluences=buildMissingInfs,
                                 setToBindPose=setToBindpose, importUsingPreDeformedPoints=importUsingPreDeformedPoints,
                                 forceUberChunk=forceUberChunk, unskinFirst=unbindFirst,
                                 selectVertsOnly=selInsteadOfSkin,
                                 postSmooth=postSmoothSteps, postSmoothWeightDiff=postSmoothWeightDiff)

        if result is False:
            mc.confirmDialog(title="Skinner Import Errors",
                             message="Please check the Script Editor for details.",
                             button="Ok")

    def exportSkin(self, mode="browser"):
        """
        When the 'Export' button is pressed.

        Parameters:
        mode : string : Default "browser".  Also supports "temp".
        """
        try:
            utils.getMeshVertIds()
        except AssertionError:
            om2.MGlobal.displayError("Skinner: No mesh/verts are selected to export skin weights on.")
            return

        vcCmd = self.widget_vcCmd.text().strip()
        if vcCmd:
            stringFormatted = False
            for sfmt in ("'%s'", '"%s"'):
                if sfmt in vcCmd:
                    stringFormatted = True
                    break
            if not stringFormatted:
                om2.MGlobal.displayError("Skinner: The string provided to 'Export -> Exec Command' is missing its string formatting: Must contain \"'%s'\".")
                return
        else:
            vcCmd = None

        vcDepotRoot = self.widget_depotRoot.text()
        if vcDepotRoot:
            if not os.path.isdir(vcDepotRoot):
                om2.MGlobal.displayError("The 'Export -> Depot Root' is an invalid directory: Please choose a valid dir, or clear the field by canceling the dir browser.")
                return

        path = None
        if mode == "browser":
            if len(self.weightPaths) != 1:
                # This sets self.weightPaths :
                self.cbFileBrowser("export")
                if not self.weightPaths:
                    om2.MGlobal.displayInfo("Exiting export: No path choosen.")
                    return
            path = self.weightPaths[0]
            self.settings.setValue(SETTING_LAST_SAVE_PATH, os.path.dirname(path))
        elif mode == "temp":
            path = core.TEMP_FILE_PATH

        verbose = True if int(self.widget_verboseLogging.checkState()) else False

        setToBindPose = self.widget_exportSetBindpose.isChecked()

        try:
            result = core.exportSkin(items=None, filePath=path, verbose=verbose,
                                     vcExportCmd=vcCmd, vcDepotRoot=vcDepotRoot,
                                     setToBindPose=setToBindPose)
            if result is False:
                mc.confirmDialog(title="Skinner Export Errors",
                                 message="Please check the Script Editor for details.",
                                 button="Ok")
            else:
                om2.MGlobal.displayInfo("Exported : %s"%path)
        except Exception as e:
            print(e)
            om2.MGlobal.displayError("Encountered an export error, plase see above ^")
