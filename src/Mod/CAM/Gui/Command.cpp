/***************************************************************************
 *   Copyright (c) 2014 Yorik van Havre <yorik@uncreated.net>              *
 *                                                                         *
 *   This file is part of the FreeCAD CAx development system.              *
 *                                                                         *
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Library General Public           *
 *   License as published by the Free Software Foundation; either          *
 *   version 2 of the License, or (at your option) any later version.      *
 *                                                                         *
 *   This library  is distributed in the hope that it will be useful,      *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this library; see the file COPYING.LIB. If not,    *
 *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
 *   Suite 330, Boston, MA  02111-1307, USA                                *
 *                                                                         *
 ***************************************************************************/

#include "PreCompiled.h"
#ifndef _PreComp_
#include <TopExp_Explorer.hxx>
#endif

#include <Base/Console.h>
#include <Gui/Application.h>
#include <Gui/Command.h>
#include <Gui/Document.h>
#include <Gui/Selection/Selection.h>
#include <Gui/Selection/SelectionObject.h>
#include <Mod/CAM/App/FeatureArea.h>
#include <Mod/CAM/App/FeaturePathShape.h>


// Path Area
// #####################################################################################################

DEF_STD_CMD_A(CmdPathArea)

CmdPathArea::CmdPathArea()
    : Command("CAM_Area")
{
    sAppModule = "Path";
    sGroup = QT_TR_NOOP("CAM");
    sMenuText = QT_TR_NOOP("Area");
    sToolTipText = QT_TR_NOOP("Creates a feature area from selected objects");
    sWhatsThis = "CAM_Area";
    sStatusTip = sToolTipText;
    sPixmap = "CAM_Area";
}

void CmdPathArea::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    std::list<std::string> cmds;
    std::ostringstream sources;
    std::string areaName;
    bool addView = true;
    for (const Gui::SelectionObject& selObj :
         getSelection().getSelectionEx(nullptr, Part::Feature::getClassTypeId())) {
        const Part::Feature* pcObj = static_cast<const Part::Feature*>(selObj.getObject());
        const std::vector<std::string>& subnames = selObj.getSubNames();
        if (addView && !areaName.empty()) {
            addView = false;
        }

        if (subnames.empty()) {
            if (addView && pcObj->isDerivedFrom<Path::FeatureArea>()) {
                areaName = pcObj->getNameInDocument();
            }
            sources << "FreeCAD.activeDocument()." << pcObj->getNameInDocument() << ",";
            continue;
        }
        for (const std::string& name : subnames) {
            if (name.compare(0, 4, "Face") && name.compare(0, 4, "Edge")) {
                Base::Console().error("Selected shape is not 2D\n");
                return;
            }

            std::ostringstream subname;
            subname << pcObj->getNameInDocument() << '_' << name;
            std::string sub_fname = getUniqueObjectName(subname.str().c_str());

            std::ostringstream cmd;
            cmd << "FreeCAD.activeDocument().addObject('Part::Feature','" << sub_fname
                << "').Shape = PathCommands.findShape(FreeCAD.activeDocument()."
                << pcObj->getNameInDocument() << ".Shape,'" << name << "'";
            if (!name.compare(0, 4, "Edge")) {
                cmd << ",'Wires'";
            }
            cmd << ')';
            cmds.push_back(cmd.str());
            sources << "FreeCAD.activeDocument()." << sub_fname << ",";
        }
    }
    if (addView && !areaName.empty()) {
        std::string FeatName = getUniqueObjectName("FeatureAreaView");
        openCommand(QT_TRANSLATE_NOOP("Command", "Create Path Area View"));
        doCommand(Doc,
                  "FreeCAD.activeDocument().addObject('Path::FeatureAreaView','%s')",
                  FeatName.c_str());
        doCommand(Doc,
                  "FreeCAD.activeDocument().%s.Source = FreeCAD.activeDocument().%s",
                  FeatName.c_str(),
                  areaName.c_str());
        commitCommand();
        updateActive();
        return;
    }
    std::string FeatName = getUniqueObjectName("FeatureArea");
    openCommand(QT_TRANSLATE_NOOP("Command", "Create Path Area"));
    doCommand(Doc, "import PathCommands");
    for (const std::string& cmd : cmds) {
        doCommand(Doc, "%s", cmd.c_str());
    }
    doCommand(Doc,
              "FreeCAD.activeDocument().addObject('Path::FeatureArea','%s')",
              FeatName.c_str());
    doCommand(Doc,
              "FreeCAD.activeDocument().%s.Sources = [ %s ]",
              FeatName.c_str(),
              sources.str().c_str());
    commitCommand();
    updateActive();
}

bool CmdPathArea::isActive()
{
    return hasActiveDocument();
}


DEF_STD_CMD_A(CmdPathAreaWorkplane)

CmdPathAreaWorkplane::CmdPathAreaWorkplane()
    : Command("CAM_Area_Workplane")
{
    sAppModule = "Path";
    sGroup = QT_TR_NOOP("CAM");
    sMenuText = QT_TR_NOOP("Area workplane");
    sToolTipText = QT_TR_NOOP("Select a workplane for a FeatureArea");
    sWhatsThis = "CAM_Area_Workplane";
    sStatusTip = sToolTipText;
    sPixmap = "CAM_Area_Workplane";
}

void CmdPathAreaWorkplane::activated(int iMsg)
{
    Q_UNUSED(iMsg);

    std::string areaName;
    std::string planeSubname;
    std::string planeName;

    for (Gui::SelectionObject& selObj :
         getSelection().getSelectionEx(nullptr, Part::Feature::getClassTypeId())) {
        const std::vector<std::string>& subnames = selObj.getSubNames();
        if (subnames.size() > 1) {
            Base::Console().error("Please select one sub shape object for plane only\n");
            return;
        }
        const Part::Feature* pcObj = static_cast<Part::Feature*>(selObj.getObject());
        if (subnames.empty()) {
            if (pcObj->isDerivedFrom<Path::FeatureArea>()) {
                if (!areaName.empty()) {
                    Base::Console().error("Please select one FeatureArea only\n");
                    return;
                }
                areaName = pcObj->getNameInDocument();
                continue;
            }
            for (TopExp_Explorer it(pcObj->Shape.getShape().getShape(), TopAbs_SHELL); it.More();
                 it.Next()) {
                Base::Console().error("Selected shape is not 2D\n");
                return;
            }
        }
        if (!planeName.empty()) {
            Base::Console().error("Please select one shape object for plane only\n");
            return;
        }
        else {
            planeSubname = planeName = pcObj->getNameInDocument();
            planeSubname += ".Shape";
        }

        for (const std::string& name : subnames) {
            if (name.compare(0, 4, "Face") && name.compare(0, 4, "Edge")) {
                Base::Console().error("Selected shape is not 2D\n");
                return;
            }
            std::ostringstream subname;
            subname << planeSubname << ",'" << name << "','Wires'";
            planeSubname = subname.str();
        }
    }
    if (areaName.empty()) {
        Base::Console().error("Please select one FeatureArea\n");
        return;
    }
    if (planeName.empty()) {
        Base::Console().error("Please select one shape object\n");
        return;
    }

    openCommand(QT_TRANSLATE_NOOP("Command", "Select Workplane for Path Area"));
    doCommand(Doc, "import PathCommands");
    doCommand(Doc,
              "FreeCAD.activeDocument().%s.WorkPlane = PathCommands.findShape("
              "FreeCAD.activeDocument().%s)",
              areaName.c_str(),
              planeSubname.c_str());
    doCommand(Doc, "FreeCAD.activeDocument().%s.ViewObject.Visibility = True", areaName.c_str());
    commitCommand();
    updateActive();
}

bool CmdPathAreaWorkplane::isActive()
{
    return !getSelection().getSelectionEx(nullptr, Path::FeatureArea::getClassTypeId()).empty();
}


// Path compound
// #####################################################################################################


DEF_STD_CMD_A(CmdPathCompound)

CmdPathCompound::CmdPathCompound()
    : Command("CAM_Compound")
{
    sAppModule = "Path";
    sGroup = QT_TR_NOOP("CAM");
    sMenuText = QT_TR_NOOP("Compound");
    sToolTipText = QT_TR_NOOP("Creates a compound from selected toolpaths");
    sWhatsThis = "CAM_Compound";
    sStatusTip = sToolTipText;
    sPixmap = "CAM_Compound";
}

void CmdPathCompound::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    std::vector<Gui::SelectionSingleton::SelObj> Sel = getSelection().getSelection();
    if (!Sel.empty()) {
        std::ostringstream cmd;
        cmd << "[";
        Path::Feature* pcPathObject;
        for (std::vector<Gui::SelectionSingleton::SelObj>::const_iterator it = Sel.begin();
             it != Sel.end();
             ++it) {
            if ((*it).pObject->isDerivedFrom<Path::Feature>()) {
                pcPathObject = static_cast<Path::Feature*>((*it).pObject);
                cmd << "FreeCAD.activeDocument()." << pcPathObject->getNameInDocument() << ",";
            }
            else {
                Base::Console().error(
                    "Only Path objects must be selected before running this command\n");
                return;
            }
        }
        cmd << "]";
        std::string FeatName = getUniqueObjectName("PathCompound");
        openCommand(QT_TRANSLATE_NOOP("Command", "Create Path Compound"));
        doCommand(Doc,
                  "FreeCAD.activeDocument().addObject('Path::FeatureCompound','%s')",
                  FeatName.c_str());
        doCommand(Doc,
                  "FreeCAD.activeDocument().%s.Group = %s",
                  FeatName.c_str(),
                  cmd.str().c_str());
        commitCommand();
        updateActive();
    }
    else {
        Base::Console().error("At least one Path object must be selected\n");
        return;
    }
}

bool CmdPathCompound::isActive()
{
    return hasActiveDocument();
}

// Path Shape
// #####################################################################################################


DEF_STD_CMD_A(CmdPathShape)

CmdPathShape::CmdPathShape()
    : Command("CAM_Shape")
{
    sAppModule = "Path";
    sGroup = QT_TR_NOOP("CAM");
    sMenuText = QT_TR_NOOP("From Shape");
    sToolTipText = QT_TR_NOOP("Creates a toolpath from a selected shape");
    sWhatsThis = "CAM_Shape";
    sStatusTip = sToolTipText;
    sPixmap = "CAM_Shape";
}

void CmdPathShape::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    std::list<std::string> cmds;
    std::ostringstream sources;
    for (const Gui::SelectionObject& selObj :
         getSelection().getSelectionEx(nullptr, Part::Feature::getClassTypeId())) {
        const Part::Feature* pcObj = static_cast<const Part::Feature*>(selObj.getObject());
        const std::vector<std::string>& subnames = selObj.getSubNames();
        if (subnames.empty()) {
            sources << "FreeCAD.activeDocument()." << pcObj->getNameInDocument() << ",";
            continue;
        }
        for (const std::string& name : subnames) {
            if (name.compare(0, 4, "Face") && name.compare(0, 4, "Edge")) {
                Base::Console().warning("Ignored shape %s %s\n",
                                        pcObj->getNameInDocument(),
                                        name.c_str());
                continue;
            }

            std::ostringstream subname;
            subname << pcObj->getNameInDocument() << '_' << name;
            std::string sub_fname = getUniqueObjectName(subname.str().c_str());

            std::ostringstream cmd;
            cmd << "FreeCAD.activeDocument().addObject('Part::Feature','" << sub_fname
                << "').Shape = PathCommands.findShape(FreeCAD.activeDocument()."
                << pcObj->getNameInDocument() << ".Shape,'" << name << "'";
            if (!name.compare(0, 4, "Edge")) {
                cmd << ",'Wires'";
            }
            cmd << ')';
            cmds.push_back(cmd.str());
            sources << "FreeCAD.activeDocument()." << sub_fname << ",";
        }
    }
    std::string FeatName = getUniqueObjectName("PathShape");
    openCommand(QT_TRANSLATE_NOOP("Command", "Create Path Shape"));
    doCommand(Doc, "import PathCommands");
    for (const std::string& cmd : cmds) {
        doCommand(Doc, "%s", cmd.c_str());
    }
    doCommand(Doc,
              "FreeCAD.activeDocument().addObject('Path::FeatureShape','%s')",
              FeatName.c_str());
    doCommand(Doc,
              "FreeCAD.activeDocument().%s.Sources = [ %s ]",
              FeatName.c_str(),
              sources.str().c_str());
    commitCommand();
    updateActive();
}

bool CmdPathShape::isActive()
{
    return hasActiveDocument();
}


void CreatePathCommands()
{
    Gui::CommandManager& rcCmdMgr = Gui::Application::Instance->commandManager();
    rcCmdMgr.addCommand(new CmdPathCompound());
    rcCmdMgr.addCommand(new CmdPathShape());
    rcCmdMgr.addCommand(new CmdPathArea());
    rcCmdMgr.addCommand(new CmdPathAreaWorkplane());
}
