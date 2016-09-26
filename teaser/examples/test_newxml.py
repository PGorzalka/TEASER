from teaser.project import Project
from teaser.logic.buildingobjects.buildingphysics.outerwall import OuterWall
import uuid
import teaser.data.output.buildingelement_output as be
print(uuid.uuid1())
print(type(str(uuid.uuid1())))

from teaser.data.dataclass import DataClass
from teaser.logic.buildingobjects.buildingphysics.material import Material
from teaser.logic.buildingobjects.buildingphysics.outerwall import OuterWall
from teaser.logic.buildingobjects.buildingphysics.rooftop import Rooftop
from teaser.logic.buildingobjects.buildingphysics.groundfloor import GroundFloor

dc_old = DataClass(type_element_file="TypeBuildingElements_039.xml")
dc_new = DataClass()

material_dict = {}
import re
regex = re.compile('[^a-zA-z0-9]')

def write_dict(pyxb_element):
    for pyxb_layer in pyxb_element.Layers.layer:
        mat = Material(parent=None)
        material_dict[regex.sub('', pyxb_layer.Material.name)] = [mat,
                                                                  mat.material_id,
                                   pyxb_layer.Material.density,
                                   pyxb_layer.Material.thermal_conduc,
                                   pyxb_layer.Material.heat_capac]
    return material_dict


for pyxb_wall in dc_old.element_bind.OuterWall:
    material_dict = write_dict(pyxb_wall)

for pyxb_roof in dc_old.element_bind.Rooftop:
    write_dict(pyxb_roof)

for pyxb_roof in dc_old.element_bind.GroundFloor:
    write_dict(pyxb_roof)


for pyxb_wall in dc_old.element_bind.OuterWall:
    out_wall = OuterWall()
    out_wall.load_type_element(pyxb_wall.building_age_group[0]+2,
                               pyxb_wall.construction_type,
                               dc_old)
    for lay in out_wall.layer:
        lay.material.material_id = material_dict[lay.material.name][1]

    out_wall.save_type_element(data_class=dc_new)

for pyxb_wall in dc_old.element_bind.Rooftop:
    roof = Rooftop()
    roof.load_type_element(pyxb_wall.building_age_group[0] + 2,
                               pyxb_wall.construction_type,
                               dc_old)
    for lay in roof.layer:
        lay.material.material_id = material_dict[lay.material.name][1]

    roof.save_type_element(data_class=dc_new)

for pyxb_wall in dc_old.element_bind.GroundFloor:
    gf = GroundFloor()
    gf.load_type_element(pyxb_wall.building_age_group[0] + 2,
                               pyxb_wall.construction_type,
                               dc_old)
    for lay in gf.layer:
        lay.material.material_id = material_dict[lay.material.name][1]

    gf.save_type_element(data_class=dc_new)


for key, value in material_dict.items():
    value[0].name = key
    value[0].density = value[2]
    value[0].thermal_conduc = value[3]
    value[0].heat_capac = value[4]
    value[0].save_material_template(data_class=dc_new)



        #mat.name = pyxb_layer.Material.name
        #mat.save_material_template(data_class=dc_new)


