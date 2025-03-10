#**************************************************************************
#   Copyright (c) 2011 Juergen Riegel <FreeCAD@juergen-riegel.net>        *
#                                                                         *
#   This file is part of the FreeCAD CAx development system.              *
#                                                                         *
#   This program is free software; you can redistribute it and/or modify  *
#   it under the terms of the GNU Lesser General Public License (LGPL)    *
#   as published by the Free Software Foundation; either version 2 of     *
#   the License, or (at your option) any later version.                   *
#   for detail see the LICENCE text file.                                 *
#                                                                         *
#   FreeCAD is distributed in the hope that it will be useful,            *
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#   GNU Library General Public License for more details.                  *
#                                                                         *
#   You should have received a copy of the GNU Library General Public     *
#   License along with FreeCAD; if not, write to the Free Software        *
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#   USA                                                                   *
#**************************************************************************

import FreeCAD
import FreeCADGui
import os
import sys
import unittest
import Sketcher
import Part
import PartDesign
import PartDesignGui
import tempfile

from PySide import QtGui, QtCore
from PySide.QtGui import QApplication

from PartDesignTests.TestMaterial import TestMaterial
from PartDesignTests.TestActiveObject import TestActiveObject

#timer runs this class in order to access modal dialog
class CallableCheckWorkflow:
    def __init__(self, test):
        self.test = test
    def __call__(self):
        dialog = QApplication.activeModalWidget()
        self.test.assertIsNotNone(dialog, "Dialog box could not be found")
        if (dialog is not None):
            dialogcheck = CallableCheckDialogWasClosed(self.test)
            QtCore.QTimer.singleShot(500, dialogcheck)
            QtCore.QTimer.singleShot(0, dialog, QtCore.SLOT('accept()'))

class CallableCheckDialogWasClosed:
    def __init__(self, test):
        self.test = test
    def __call__(self):
        dialog = QApplication.activeModalWidget()
        self.test.assertIsNone(dialog, "Dialog box was not closed by accept()")

class CallableCheckWarning:
    def __init__(self, test):
        self.test = test
    def __call__(self):
        dialog = QApplication.activeModalWidget()
        self.test.assertIsNotNone(dialog, "Input dialog box could not be found")
        if (dialog is not None):
            QtCore.QTimer.singleShot(0, dialog, QtCore.SLOT('accept()'))

class CallableComboBox:
    def __init__(self, test):
        self.test = test
    def __call__(self):
        dialog = QApplication.activeModalWidget()
        self.test.assertIsNotNone(dialog, "Warning dialog box could not be found")
        if (dialog is not None):
            cbox = dialog.findChild(QtGui.QComboBox)
            self.test.assertIsNotNone(cbox, "ComboBox widget could not be found")
            if (cbox is not None):
                QtCore.QTimer.singleShot(0, dialog, QtCore.SLOT('accept()'))

App = FreeCAD
Gui = FreeCADGui
#---------------------------------------------------------------------------
# define the test cases to test the FreeCAD PartDesign module
#---------------------------------------------------------------------------
class PartDesignGuiTestCases(unittest.TestCase):
    def setUp(self):
        self.Doc = FreeCAD.newDocument("SketchGuiTest")

    def testRefuseToMoveSingleFeature(self):
        FreeCAD.Console.PrintMessage('Testing refuse to move the feature with dependencies from one body to another\n')
        self.BodySource = self.Doc.addObject('PartDesign::Body','Body')
        Gui.activateView('Gui::View3DInventor', True)
        Gui.activeView().setActiveObject('pdbody', self.BodySource)

        self.BoxObj = self.Doc.addObject('PartDesign::AdditiveBox','Box')
        self.BoxObj.Length=10.0
        self.BoxObj.Width=10.0
        self.BoxObj.Height=10.0
        self.BodySource.addObject(self.BoxObj)

        App.ActiveDocument.recompute()

        self.Sketch = self.Doc.addObject('Sketcher::SketchObject','Sketch')
        self.Sketch.AttachmentSupport = (self.BoxObj, ('Face3',))
        self.Sketch.MapMode = 'FlatFace'
        self.BodySource.addObject(self.Sketch)

        geoList = []
        geoList.append(Part.LineSegment(App.Vector(2.0,8.0,0),App.Vector(8.0,8.0,0)))
        geoList.append(Part.LineSegment(App.Vector(8.0,8.0,0),App.Vector(8.0,2.0,0)))
        geoList.append(Part.LineSegment(App.Vector(8.0,2.0,0),App.Vector(2.0,2.0,0)))
        geoList.append(Part.LineSegment(App.Vector(2.0,2.0,0),App.Vector(2.0,8.0,0)))
        self.Sketch.addGeometry(geoList,False)
        conList = []
        conList.append(Sketcher.Constraint('Coincident',0,2,1,1))
        conList.append(Sketcher.Constraint('Coincident',1,2,2,1))
        conList.append(Sketcher.Constraint('Coincident',2,2,3,1))
        conList.append(Sketcher.Constraint('Coincident',3,2,0,1))
        conList.append(Sketcher.Constraint('Horizontal',0))
        conList.append(Sketcher.Constraint('Horizontal',2))
        conList.append(Sketcher.Constraint('Vertical',1))
        conList.append(Sketcher.Constraint('Vertical',3))
        self.Sketch.addConstraint(conList)

        self.Pad = self.Doc.addObject("PartDesign::Pad","Pad")
        self.Pad.Profile = self.Sketch
        self.Pad.Length = 10.000000
        self.Pad.Length2 = 100.000000
        self.Pad.Type = 0
        self.Pad.UpToFace = None
        self.Pad.Reversed = 0
        self.Pad.Midplane = 0
        self.Pad.Offset = 0.000000

        self.BodySource.addObject(self.Pad)

        self.Doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")

        self.BodyTarget = self.Doc.addObject('PartDesign::Body','Body')

        Gui.Selection.addSelection(App.ActiveDocument.Pad)
        cobj = CallableCheckWarning(self)
        QtCore.QTimer.singleShot(500, cobj)
        Gui.runCommand('PartDesign_MoveFeature')
        #assert dependencies of the Sketch
        self.assertEqual(len(self.BodySource.Group), 3, "Source body feature count is wrong")
        self.assertEqual(len(self.BodyTarget.Group), 0, "Target body feature count is wrong")

    def testMoveSingleFeature(self):
        FreeCAD.Console.PrintMessage('Testing moving one feature from one body to another\n')
        self.BodySource = self.Doc.addObject('PartDesign::Body','Body')
        Gui.activateView('Gui::View3DInventor', True)
        Gui.activeView().setActiveObject('pdbody', self.BodySource)

        self.Sketch = self.Doc.addObject('Sketcher::SketchObject','Sketch')
        self.BodySource.addObject(self.Sketch)
        self.Sketch.AttachmentSupport = (self.BodySource.Origin.OriginFeatures[3], [''])
        self.Sketch.MapMode = 'FlatFace'


        geoList = []
        geoList.append(Part.LineSegment(App.Vector(-10.000000,10.000000,0),App.Vector(10.000000,10.000000,0)))
        geoList.append(Part.LineSegment(App.Vector(10.000000,10.000000,0),App.Vector(10.000000,-10.000000,0)))
        geoList.append(Part.LineSegment(App.Vector(10.000000,-10.000000,0),App.Vector(-10.000000,-10.000000,0)))
        geoList.append(Part.LineSegment(App.Vector(-10.000000,-10.000000,0),App.Vector(-10.000000,10.000000,0)))
        self.Sketch.addGeometry(geoList,False)
        conList = []
        conList.append(Sketcher.Constraint('Coincident',0,2,1,1))
        conList.append(Sketcher.Constraint('Coincident',1,2,2,1))
        conList.append(Sketcher.Constraint('Coincident',2,2,3,1))
        conList.append(Sketcher.Constraint('Coincident',3,2,0,1))
        conList.append(Sketcher.Constraint('Horizontal',0))
        conList.append(Sketcher.Constraint('Horizontal',2))
        conList.append(Sketcher.Constraint('Vertical',1))
        conList.append(Sketcher.Constraint('Vertical',3))
        self.Sketch.addConstraint(conList)

        self.Pad = self.Doc.addObject("PartDesign::Pad","Pad")
        self.BodySource.addObject(self.Pad)
        self.Pad.Profile = self.Sketch
        self.Pad.Length = 10.000000
        self.Pad.Length2 = 100.000000
        self.Pad.Type = 0
        self.Pad.UpToFace = None
        self.Pad.Reversed = 0
        self.Pad.Midplane = 0
        self.Pad.Offset = 0.000000

        self.Doc.recompute()
        Gui.SendMsgToActiveView("ViewFit")

        self.BodyTarget = self.Doc.addObject('PartDesign::Body','Body')

        Gui.Selection.addSelection(App.ActiveDocument.Pad)
        cobj = CallableComboBox(self)
        QtCore.QTimer.singleShot(500, cobj)
        Gui.runCommand('PartDesign_MoveFeature')
        #assert dependencies of the Sketch
        self.Doc.recompute()

        self.assertFalse(self.Sketch.AttachmentSupport[0][0] in self.BodySource.Origin.OriginFeatures)
        self.assertTrue(self.Sketch.AttachmentSupport[0][0] in self.BodyTarget.Origin.OriginFeatures)
        self.assertEqual(len(self.BodySource.Group), 0, "Source body feature count is wrong")
        self.assertEqual(len(self.BodyTarget.Group), 2, "Target body feature count is wrong")

    def tearDown(self):
        FreeCAD.closeDocument("SketchGuiTest")

class PartDesignTransformed(unittest.TestCase):
    def setUp(self):
        self.Doc = App.newDocument("PartDesignTransformed")
        self.Body = self.Doc.addObject('PartDesign::Body','Body')
        self.BoxObj = self.Doc.addObject('PartDesign::AdditiveBox','Box')
        self.BoxObj.Length=10.0
        self.BoxObj.Width=10.0
        self.BoxObj.Height=10.0
        App.ActiveDocument.recompute()
        #not adding box to the body to imitate undertermined workflow
        tempDir = tempfile.gettempdir()
        self.TempDoc = os.path.join(tempDir, 'PartDesignTransformed.FCStd')
        App.ActiveDocument.saveAs(self.TempDoc)
        App.closeDocument("PartDesignTransformed")

    def testMultiTransformCase(self):
        App.Console.PrintMessage('Testing applying MultiTransform to the Box outside the body\n')
        App.open(self.TempDoc)
        App.setActiveDocument("PartDesignTransformed")
        Gui.Selection.addSelection(App.ActiveDocument.Box)

        workflowcheck = CallableCheckWorkflow(self)
        QtCore.QTimer.singleShot(500, workflowcheck)
        Gui.runCommand("PartDesign_MultiTransform")

        App.closeDocument("PartDesignTransformed")

    def tearDown(self):
        #closing doc
        if (App.ActiveDocument is not None and App.ActiveDocument.Name == PartDesignTransformed):
            App.closeDocument("PartDesignTransformed")
        #print ("omit closing document for debugging")

#class PartDesignGuiTestCases(unittest.TestCase):
#   def setUp(self):
#       self.Doc = FreeCAD.newDocument("SketchGuiTest")
#
#   def testBoxCase(self):
#       self.Box = self.Doc.addObject('PartDesign::SketchObject','SketchBox')
#       self.Box.addGeometry(Part.LineSegment(App.Vector(-99.230339,36.960674,0),App.Vector(69.432587,36.960674,0)))
#       self.Box.addGeometry(Part.LineSegment(App.Vector(69.432587,36.960674,0),App.Vector(69.432587,-53.196629,0)))
#       self.Box.addGeometry(Part.LineSegment(App.Vector(69.432587,-53.196629,0),App.Vector(-99.230339,-53.196629,0)))
#       self.Box.addGeometry(Part.LineSegment(App.Vector(-99.230339,-53.196629,0),App.Vector(-99.230339,36.960674,0)))
#
#   def tearDown(self):
#       #closing doc
#       FreeCAD.closeDocument("SketchGuiTest")

class TestShapeBinder(unittest.TestCase):
    def setUp(self):
        self.Doc = FreeCAD.newDocument("PartDesignTestShapeBinder")

    def testDefaultColor(self):
        """
        A shape binder uses a different default color than a Part feature.
        This color must still be set after its creation.
        """
        self.Body = self.Doc.addObject('PartDesign::Body','Body')
        self.Box = self.Doc.addObject('PartDesign::AdditiveBox','Box')
        self.Body.addObject(self.Box)
        self.Doc.recompute()
        binder = self.Doc.addObject('PartDesign::ShapeBinder','ShapeBinder')
        binder.Support = [(self.Box, 'Face1')]

        grp = App.ParamGet("User parameter:BaseApp/Preferences/Mod/PartDesign")
        packed_color = grp.GetUnsigned("DefaultDatumColor", 0xFFD70099)
        r, g, b, a = binder.ViewObject.ShapeColor
        color = int(r * 255.0 + 0.5) << 24 | int(g * 255.0 + 0.5) << 16 | int(b * 255.0 + 0.5) << 8 | int(a * 255.0 + 0.5)

        self.assertEqual(packed_color, color)

    def tearDown(self):
        FreeCAD.closeDocument(self.Doc.Name)


class TestSubShapeBinder(unittest.TestCase):
    def setUp(self):
        self.Doc = FreeCAD.newDocument("PartDesignTestSubShapeBinder")

    def tearDown(self):
        FreeCAD.closeDocument(self.Doc.Name)

    def testDefaultColor(self):
        """
        A sub-shape binder uses a different default color than a Part feature.
        This color must still be set after its creation.
        """
        body = self.Doc.addObject('PartDesign::Body','Body')
        box = self.Doc.addObject('PartDesign::AdditiveBox','Box')
        body.addObject(box)

        self.Doc.recompute()
        binder = body.newObject('PartDesign::SubShapeBinder','Binder')
        binder.Support = [(box, ("Face1"))]

        grp = App.ParamGet("User parameter:BaseApp/Preferences/Mod/PartDesign")
        packed_color = grp.GetUnsigned("DefaultDatumColor", 0xFFD70099)
        r, g, b, a = binder.ViewObject.ShapeColor
        color = int(r * 255.0 + 0.5) << 24 | int(g * 255.0 + 0.5) << 16 | int(b * 255.0 + 0.5) << 8 | int(a * 255.0 + 0.5)

        self.assertEqual(packed_color, color)


class TestDatumPlane(unittest.TestCase):
    def setUp(self):
        self.Doc = FreeCAD.newDocument("PartDesignTestDatumPlane")

    def tearDown(self):
        FreeCAD.closeDocument(self.Doc.Name)

    def testDefaultColor(self):
        """
        A datum object uses a different default color than a Part feature.
        This color must still be set after its creation.
        """
        body = self.Doc.addObject('PartDesign::Body','Body')
        box = self.Doc.addObject('PartDesign::AdditiveBox','Box')
        body.addObject(box)

        self.Doc.recompute()
        datum = body.newObject('PartDesign::Plane','DatumPlane')
        datum.AttachmentSupport = [(box, 'Face6')]
        datum.MapMode = 'FlatFace'
        self.Doc.recompute()

        grp = App.ParamGet("User parameter:BaseApp/Preferences/Mod/PartDesign")
        packed_color = grp.GetUnsigned("DefaultDatumColor", 0xFFD70099)
        r, g, b, a = datum.ViewObject.ShapeColor
        color = int(r * 255.0 + 0.5) << 24 | int(g * 255.0 + 0.5) << 16 | int(b * 255.0 + 0.5) << 8 | int(a * 255.0 + 0.5)

        self.assertEqual(packed_color, color)
