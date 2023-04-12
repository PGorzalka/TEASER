# created June 2015
# by TEASER4 Development Team


from teaser.logic.buildingobjects.buildingphysics.wall\
    import Wall


class InnerWall(Wall):
    """InnerWall class

    This class holds information for an inner wall and is a child of Wall()

    Parameters
    ----------

    parent : ThermalZone()
        The parent class of this object, the ThermalZone the BE belongs to.
        Allows for better control of hierarchical structures. If not None it
        adds this InnerWall to ThermalZone.inner_walls.
        Default is None.

    Attributes
    ----------

    internal_id : float
        Random id for the distinction between different elements.
    name : str
        Individual name
    construction_type : str
        Type of construction (e.g. "heavy" or "light"). Needed for
        distinction between different constructions types in the same
        building age period.
    year_of_retrofit : int
        Year of last retrofit
    year_of_construction : int
        Year of first construction
    building_age_group : list
        Determines the building age period that this building
        element belongs to [begin, end], e.g. [1984, 1994]
    area : float [m2]
        Area of building element
    tilt : float [degree]
        Tilt against horizontal, default is 90.0
    orientation : float [degree]
        Azimuth direction of building element (0 : north, 90: east, 180: south,
        270: west)
    inner_convection : float [W/(m2*K)]
        Constant heat transfer coefficient of convection inner side (facing
        the zone), default 1.7
    inner_radiation : float [W/(m2*K)]
        Constant heat transfer coefficient of radiation inner side (facing
        the zone), default 5.0
    outer_convection : float [W/(m2*K)]
        Constant heat transfer coefficient of convection outer side (facing
        the ambient or adjacent zone). Default 0.0 - if unchanged, 1.7 when
        adding an outside
    outer_radiation : float [W/(m2*K)]
        Constant heat transfer coefficient of radiation outer side (facing
        the ambient or adjacent zone). Default 0.0 - if unchanged, 5.0 when
        adding an outside
    layer : list
        List of all layers of a building element (to be filled with Layer
        objects). Use element.layer = None to delete all layers of the building
        element
    outside : ThermalZone()
        the thermal zone to the outside of the wall. If None, same zone is on
        the outside.

    Calculated Attributes

    r1 : float [K/W]
        equivalent resistance R1 of the analogous model given in VDI 6007
    r2 : float [K/W]
        equivalent resistance R2 of the analogous model given in VDI 6007
    r3 : float [K/W]
        equivalent resistance R3 of the analogous model given in VDI 6007
    c1 : float [J/K]
        equivalent capacity C1 of the analogous model given in VDI 6007
    c2 : float [J/K]
        equivalent capacity C2 of the analogous model given in VDI 6007
    c1_korr : float [J/K]
        corrected capacity C1,korr for building elements in the case of
        asymmetrical thermal load given in VDI 6007
    ua_value : float [W/K]
        UA-Value of building element (Area times U-Value)
    r_inner_conv : float [K/W]
        Convective resistance of building element on inner side (facing the
        zone)
    r_inner_rad : float [K/W]
        Radiative resistance of building element on inner side (facing the
        zone)
    r_inner_conv : float [K/W]
        Combined convective and radiative resistance of building element on
        inner side (facing the zone)
    r_outer_conv : float [K/W]
        Convective resistance of building element on outer side (facing
        the ambient or adjacent zone). Currently for all InnerWalls and
        GroundFloors this value is set to 0.0
    r_outer_rad : float [K/W]
        Radiative resistance of building element on outer side (facing
        the ambient or adjacent zone). Currently for all InnerWalls and
        GroundFloors this value is set to 0.0
    r_outer_conv : float [K/W]
        Combined convective and radiative resistance of building element on
        outer side (facing the ambient or adjacent zone). Currently for all
        InnerWalls and GroundFloors this value is set to 0.0
    wf_out : float
        Weightfactor of building element ua_value/ua_value_zone
    """

    def __init__(self, parent=None, outside=None):
        """
        """
        super(InnerWall, self).__init__(parent, outside)

        self._tilt = 90.0
        self._inner_convection = 1.7
        self._inner_radiation = 5.0
        if self._outside is None:
            self._outer_convection = None
            self._outer_radiation = None
        else:
            self._outer_convection = 1.7
            self._outer_radiation = 5.0

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, value):
        if value is not None:

            ass_error_1 = "Parent has to be an instance of ThermalZone()"

            assert type(value).__name__ == "ThermalZone", ass_error_1

            self.__parent = value

            if self.outside is not None:
                self.__parent.nz_borders.append(self)
            elif type(self).__name__ == "InnerWall":
                self.__parent.inner_walls.append(self)
            elif type(self).__name__ == "Ceiling":
                self.__parent.ceilings.append(self)
            elif type(self).__name__ == "Floor":
                self.__parent.floors.append(self)
            else:
                raise ValueError('Instance of InnerWall not known')

            if self.parent.parent is not None:
                self.year_of_construction = \
                    self.parent.parent.year_of_construction
            else:
                pass
        else:

            self.__parent = None