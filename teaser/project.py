"""This module includes the Project class, which is the API for TEASER."""

import warnings
import os
import re
import teaser.logic.utilities as utilities
import teaser.data.utilities as datahandling
import teaser.data.input.teaserjson_input as tjson_in
import teaser.data.output.teaserjson_output as tjson_out
import teaser.data.output.aixlib_output as aixlib_output
import teaser.data.output.ibpsa_output as ibpsa_output
from teaser.data.dataclass import DataClass
from teaser.logic.archetypebuildings.tabula.de.singlefamilyhouse import SingleFamilyHouse
from teaser.logic.simulation.modelicainfo import ModelicaInfo


class Project(object):
    """Top class for TEASER projects it serves as an API

    The Project class is the top class for all TEASER projects and serves as an
    API for script based interface. It is highly recommended to always
    instantiate the Project class before starting to work with TEASER. It
    contains functions to generate archetype buildings, to export models and to
    save information for later use.

    Parameters
    ----------
    load_data : boolean
        boolean if data bases for materials, type elements and use conditions
        should be loaded. default = False but will be automatically loaded
        once you add a archetype building. For building generation from
        scratch, set to True

    Attributes
    ----------

    name : str
        Name of the Project (default is 'Project')
    modelica_info : instance of ModelicaInfo
        TEASER instance of ModelicaInfo to store Modelica related
        information, like used compiler, start and stop time, etc.
    buildings : list
        List of all buildings in one project, instances of Building()
    data : instance of DataClass
        TEASER instance of DataClass containing JSON binding classes
    weather_file_path : str
        Absolute path to weather file used for Modelica simulation. Default
        weather file can be find in inputdata/weatherdata.
    number_of_elements_calc : int
        Defines the number of elements, that are aggregated (1, 2, 3 or 4),
        default is 2
    merge_windows_calc : bool
        True for merging the windows into the outer walls, False for
        separate resistance for window, default is False (only supported for
        IBPSA)
    used_library_calc : str
        used library (AixLib and IBPSA are supported)
    dir_reference_results : str
        Path to reference results in BuildingsPy format. If not None, the results
        will be copied into the model output directories so that the exported
        models can be regression tested against these results with BuildingsPy.
    """

    def __init__(self, load_data=False):
        """Constructor of Project Class.
        """
        self._name = "Project"
        self.modelica_info = ModelicaInfo()

        self.weather_file_path = utilities.get_full_path(
            os.path.join(
                "data",
                "input",
                "inputdata",
                "weatherdata",
                "DEU_BW_Mannheim_107290_TRY2010_12_Jahr_BBSR.mos",
            )
        )

        self.buildings = []

        self.load_data = load_data

        self._number_of_elements_calc = 2
        self._merge_windows_calc = False
        self._used_library_calc = "AixLib"

        if load_data:
           raise ValueError("This option was deprecated")
        self.data = None

        self.dir_reference_results = None

    @staticmethod
    def instantiate_data_class():
        """Initialization of DataClass

        Returns
        -------

        DataClass : Instance of DataClass()

        """
        return DataClass(construction_data=datahandling.ConstructionData.iwu_heavy)

    def calc_all_buildings(self, raise_errors=True):
        """Calculates values for all project buildings

        You need to set the following parameters in the Project class.

        number_of_elements_calc : int
            defines the number of elements, that area aggregated, between 1
            and 4, default is 2
            For AixLib you should always use 2 elements!!!

        merge_windows_calc : bool
            True for merging the windows into the outer walls, False for
            separate resistance for window, default is False
            For AixLib vdi calculation is True, ebc calculation is False

        used_library_calc : str
            used library (AixLib and IBPSA are supported)

        """
        if raise_errors is True:
            for bldg in reversed(self.buildings):
                bldg.calc_building_parameter(
                    number_of_elements=self._number_of_elements_calc,
                    merge_windows=self._merge_windows_calc,
                    used_library=self._used_library_calc,
                )
        else:
            for bldg in reversed(self.buildings):
                try:
                    bldg.calc_building_parameter(
                        number_of_elements=self._number_of_elements_calc,
                        merge_windows=self._merge_windows_calc,
                        used_library=self._used_library_calc,
                    )
                except (ZeroDivisionError, TypeError):
                    warnings.warn(
                        "Following building can't be calculated and is "
                        "removed from buildings list. Use raise_errors=True "
                        "to get python errors and stop TEASER from deleting "
                        "this building:" + bldg.name
                    )
                    self.buildings.remove(bldg)

    def retrofit_all_buildings(
            self,
            year_of_retrofit=None,
            type_of_retrofit=None,
            window_type=None,
            material=None,
    ):
        """Retrofits all buildings in the project.

        Depending on the used Archetype approach this function will retrofit
        the building. If you have archetypes of both typologies (tabula and
        iwu/BMBVS) you need to pass all keywords (see also Parameters section).

        If TABULA approach is used, it will replace the current construction
        with the construction specified in 'type_of_retrofit',
        where 'retrofit' and 'adv_retrofit' are allowed.

        'iwu' or 'BMVBS' Buildings in the project are retrofitted in the
        following manner:

        - replace all windows of the building to retrofitted window according
          to the year of retrofit.
        - add an additional insulation layer to all outer walls
          (including roof, and ground floor).
          The thickness of the insulation layer is calculated
          that the U-Value of the wall corresponds to the retrofit standard of
          the year of retrofit.
        #TODO #745: je nach eingeführter Variable für den kfw retrofit noch abändern
        - alternatively these buildings can be retrofitted to kfw-standards
          with the 'type_of_retrofit' parameter (allowed values are kfw_40, kfw_55,
          kfw_70, kfw_85 and kfw_100)

        The needed parameters for the Modelica Model are calculated
        automatically, using the calculation_method specified in the
        first scenario.

        Note: To Calculate U-Value, the standard TEASER coefficients for outer
        and inner heat transfer are used.

        Parameters
        ----------
        year_of_retrofit : int
            the year the buildings are retrofitted, only 'iwu'/'bmbvs'
            archetype approach.
        type_of_retrofit : str
            The classification of retrofit, if the archetype building
            approach of TABULA is used.
            Or if the building has to be retrofitted on kfw-standards
        window_type : str
            Default: EnEv 2014, only 'iwu'/'bmbvs' archetype approach.
        material : str
            Default: EPS035, only 'iwu'/'bmbvs' archetype approach.

        """
        #TODO #745: kfw retrofit
        ass_error_type = "only 'retrofit' and 'adv_retrofit' are valid "
        assert type_of_retrofit in [None, "adv_retrofit", "retrofit"], ass_error_type
        tabula_buildings = []
        iwu_buildings = []

        for bldg in self.buildings:
            if isinstance(bldg, SingleFamilyHouse):
                if type_of_retrofit is None:
                    raise ValueError(
                        "you need to set type_of_retrofit for " "TABULA retrofit"
                    )
                tabula_buildings.append(bldg)
            else:
                if year_of_retrofit is None:
                    raise ValueError("you need to set year_of_retrofit for " "retrofit")
                iwu_buildings.append(bldg)

        if self.data == DataClass(construction_data=datahandling.ConstructionData.iwu_heavy):
            for bld_iwu in iwu_buildings:
                bld_iwu.retrofit_building(
                    year_of_retrofit=year_of_retrofit,
                    window_type=window_type,
                    material=material,
                )
            self.data = DataClass(construction_data=datahandling.ConstructionData.tabula_de_standard)
            for bld_tabula in tabula_buildings:
                bld_tabula.retrofit_building(type_of_retrofit=type_of_retrofit)

        else:
            for bld_tabula in tabula_buildings:
                bld_tabula.retrofit_building(type_of_retrofit=type_of_retrofit)
            self.data = DataClass(construction_data=datahandling.ConstructionData.iwu_heavy)
            for bld_iwu in iwu_buildings:
                bld_iwu.retrofit_building(
                    year_of_retrofit=year_of_retrofit,
                    window_type=window_type,
                    material=material,
                )

    def add_non_residential(
            self,
            construction_data,
            geometry_data,
            name,
            year_of_construction,
            number_of_floors,
            height_of_floors,
            net_leased_area,
            with_ahu=True,
            internal_gains_mode=1,
            office_layout=None,
            window_layout=None,
    ):
        """Add a non-residential building to the TEASER project.
        #TODO #745 adjust docstring to new variables
        This function adds a non-residential archetype building to the TEASER
        project. You need to specify the method of the archetype generation.
        Currently TEASER supports only method according to Lichtmess and BMVBS
        for non-residential buildings. Further the type of geometry_data needs to be
        specified. Currently TEASER supports four different types of
        non-residential buildings ('office', 'institute', 'institute4',
        'institute8'). For more information on specific archetype buildings and
        methods, please read the docs of archetype classes.

        This function also calculates the parameters of the buildings directly
        with the settings set in the project (e.g. used_library_calc or
        number_of_elements_calc).

        Parameters
        ----------
        construction_data : str
            Used archetype method, currently only 'bmvbs' is supported
        geometry_data : str
            Main geometry_data of the obtained building, currently only 'office',
            'institute', 'institute4', institute8' are supported
        name : str
            Individual name
        year_of_construction : int
            Year of first construction
        height_of_floors : float [m]
            Average height of the buildings' floors
        number_of_floors : int
            Number of building's floors above ground
        net_leased_area : float [m2]
            Total net leased area of building. This is area is NOT the
            footprint
            of a building
        with_ahu : Boolean
            If set to True, an empty instance of BuildingAHU is instantiated
            and
            assigned to attribute central_ahu. This instance holds information
            for central Air Handling units. Default is False.
        internal_gains_mode: int [1, 2, 3]
            mode for the internal gains calculation done in AixLib:

            1. Temperature and activity degree dependent heat flux calculation for persons. The
            calculation is based on  SIA 2024 (default)

            2. Temperature and activity degree independent heat flux calculation for persons, the max.
            heatflowrate is prescribed by the parameter
            fixed_heat_flow_rate_persons.

            3. Temperature and activity degree dependent calculation with
            consideration of moisture and co2. The moisture calculation is
            based on SIA 2024 (2015) and regards persons and non-persons, the co2 calculation is based on
            Engineering ToolBox (2004) and regards only persons.

        office_layout : int
            Structure of the floor plan of office buildings, default is 1,
            which is representative for one elongated floor.

            1. elongated 1 floor

            2. elongated 2 floors

            3. compact (e.g. for a square base building)

        window_layout : int
            Structure of the window facade type, default is 1, which is
            representative for a punctuated facade.

            1. punctuated facade (individual windows)

            2. banner facade (continuous windows)

            3. full glazing

        Returns
        -------
        type_bldg : Instance of Office()

        """
        # definiere construction_data und geometry_data als enum falls noch nicht geschehen
        if isinstance(construction_data, str):
            construction_data = datahandling.ConstructionData(construction_data)
        if isinstance(geometry_data, str):
            geometry_data = datahandling.GeometryData(geometry_data)

        ass_error_construction_data = (
            "only 'iwu' is a valid construction_data for " "non-residential archetype generation"
        )

        assert construction_data.value in ["iwu_heavy", "iwu_light"], ass_error_construction_data

        ass_error_geometry_data = ("geometry_data does not match the construction_data")

        assert geometry_data in datahandling.allowed_geometries.get(construction_data, []), ass_error_geometry_data

        self.data = DataClass(construction_data)

        type_bldg = datahandling.geometries[geometry_data](
            self,
            name,
            year_of_construction,
            number_of_floors,
            height_of_floors,
            net_leased_area,
            with_ahu,
            internal_gains_mode,
            office_layout,
            window_layout,
            construction_data,
        )

        type_bldg.generate_archetype()
        type_bldg.calc_building_parameter(
            number_of_elements=self._number_of_elements_calc,
            merge_windows=self._merge_windows_calc,
            used_library=self._used_library_calc,
        )
        return type_bldg

    def add_residential(
            self,
            construction_data,
            geometry_data,
            name,
            year_of_construction,
            number_of_floors,
            height_of_floors,
            net_leased_area,
            with_ahu=False,
            internal_gains_mode=1,
            residential_layout=None,
            neighbour_buildings=None,
            attic=None,
            cellar=None,
            dormer=None,
            number_of_apartments=None,
    ):
        """Add a residential building to the TEASER project.

        This function adds a residential archetype building to the TEASER
        project. You need to specify the construction_data of the archetype generation.
        Currently TEASER supports only construction_data according 'iwu', 'urbanrenet',
        'tabula_de' and 'tabula_dk' for residential buildings. Further the
        type of geometry_data needs to be specified. Currently TEASER supports one type
        of
        residential building for 'iwu' and eleven types for 'urbanrenet'. For
        more information on specific archetype buildings and methods, please
        read the docs of archetype classes.
        This function also calculates the parameters of the buildings directly
        with the settings set in the project (e.g. used_library_calc or
        number_of_elements_calc).

        Parameters
        ----------
        #TODO #745: adjust docstring
        construction_data : str
            Used archetype construction_data, currently only 'iwu' or 'urbanrenet' are
            supported, 'tabula_de' to follow soon
        geometry_data : str
            Main geometry_data of the obtained building, currently only
            'single_family_dwelling' is supported for iwu and 'est1a', 'est1b',
            'est2', 'est3', 'est4a', 'est4b', 'est5' 'est6', 'est7', 'est8a',
            'est8b' for urbanrenet.
        name : str
            Individual name
        year_of_construction : int
            Year of first construction
        height_of_floors : float [m]
            Average height of the buildings' floors
        number_of_floors : int
            Number of building's floors above ground
        net_leased_area : float [m2]
            Total net leased area of building. This is area is NOT the
            footprint
            of a building
        with_ahu : Boolean
            If set to True, an empty instance of BuildingAHU is instantiated
            and
            assigned to attribute central_ahu. This instance holds information
            for central Air Handling units. Default is False.
        internal_gains_mode: int [1, 2, 3]
            mode for the internal gains calculation done in AixLib:

            1. Temperature and activity degree dependent heat flux calculation for persons. The
               calculation is based on  SIA 2024 (default)

            2. Temperature and activity degree independent heat flux calculation for persons, the max.
               heatflowrate is prescribed by the parameter
               fixed_heat_flow_rate_persons.

            3. Temperature and activity degree dependent calculation with
               consideration of moisture and co2. The moisture calculation is
               based on SIA 2024 (2015) and regards persons and non-persons, the co2 calculation is based on
               Engineering ToolBox (2004) and regards only persons.

        residential_layout : int
            Structure of floor plan (default = 0) CAUTION only used for iwu

            0. compact

            1. elongated/complex

        neighbour_buildings : int
            Number of neighbour buildings. CAUTION: this will not change
            the orientation of the buildings wall, but just the overall
            exterior wall and window area(!) (default = 0)

            0. no neighbour
            1. one neighbour
            2. two neighbours

        attic : int
            Design of the attic. CAUTION: this will not change the orientation
            or tilt of the roof instances, but just adapt the roof area(!) (
            default = 0) CAUTION only used for iwu

            0. flat roof
            1. non heated attic
            2. partly heated attic
            3. heated attic

        cellar : int
            Design of the of cellar CAUTION: this will not change the
            orientation, tilt of GroundFloor instances, nor the number or area
            of ThermalZones, but will change GroundFloor area(!) (default = 0)
            CAUTION only used for iwu

            0. no cellar
            1. non heated cellar
            2. partly heated cellar
            3. heated cellar

        dormer : str
            Is a dormer attached to the roof? CAUTION: this will not
            change roof or window orientation or tilt, but just adapt the roof
            area(!) (default = 0) CAUTION only used for iwu

            0. no dormer
            1. dormer

        construction_data : str
            construction_data of used wall constructions default is "iwu_heavy")

            - iwu_heavy: heavy construction
            - iwu_light: light construction
            - tabula_de
            - tabula_dk
            - kfw_40, kfw_55, kfw_70, kfw_85, kfw_100

        number_of_apartments : int
            number of apartments inside Building (default = 1). CAUTION only
            used for urbanrenet

        Returns
        -------
        type_bldg : Instance of Archetype Building

        """
        if isinstance(construction_data, str):
            construction_data = datahandling.ConstructionData(construction_data)
        if isinstance(geometry_data, str):
            geometry_data = datahandling.GeometryData(geometry_data)

        ass_error_apart = (
            "The keyword number_of_apartments does not have any "
            "effect on archetype generation for 'iwu' or"
            "'tabula_de', see docs for more information"
        )

        if (construction_data.get_prefix() in ["iwu", "tabula_de", "tabula_dk", "kfw"]
                and number_of_apartments is not None):
            warnings.warn(ass_error_apart)

        self.data = DataClass(construction_data)

        ass_error_geometry_data = ("geometry_data does not match the construction_data")

        assert geometry_data in datahandling.allowed_geometries.get(construction_data, []), ass_error_geometry_data

        common_arg = {
            'name': name,
            'year_of_construction': year_of_construction,
            'number_of_floors': number_of_floors,
            'height_of_floors': height_of_floors,
            'net_leased_area': net_leased_area,
            'with_ahu': with_ahu,
            'internal_gains_mode': internal_gains_mode,
            'construction_data': construction_data,
        }

        urbanrenet_arg = common_arg.copy()
        urbanrenet_arg.update({
            'neighbour_buildings': neighbour_buildings,
        })

        iwu_arg = common_arg.copy()
        iwu_arg.update({
            'residential_layout': residential_layout,
            'neighbour_buildings': neighbour_buildings,
            'attic': attic,
            'cellar': cellar,
            'dormer': dormer,
        })

        if geometry_data == datahandling.GeometryData.IwuSingleFamilyDwelling:
            type_bldg = datahandling.geometries[geometry_data](self, **iwu_arg)
        elif geometry_data == datahandling.GeometryData.UrbanrenetEst1a:
            type_bldg = datahandling.geometries[geometry_data](self, **urbanrenet_arg)
        elif geometry_data.value in [datahandling.GeometryData.UrbanrenetEst1b,
                                     datahandling.GeometryData.UrbanrenetEst2,
                                     datahandling.GeometryData.UrbanrenetEst3,
                                     datahandling.GeometryData.UrbanrenetEst4a,
                                     datahandling.GeometryData.UrbanrenetEst4b,
                                     datahandling.GeometryData.UrbanrenetEst5,
                                     datahandling.GeometryData.UrbanrenetEst6, datahandling.GeometryData.UrbanrenetEst7,
                                     datahandling.GeometryData.UrbanrenetEst8a,
                                     datahandling.GeometryData.UrbanrenetEst8b]:
            urbanrenet_arg['number_of_apartments'] = number_of_apartments
            type_bldg = datahandling.geometries[geometry_data](self, **urbanrenet_arg)
        else:
            type_bldg = datahandling.geometries[geometry_data](self, **common_arg)
        type_bldg.generate_archetype()
        return type_bldg

    def save_project(self, file_name=None, path=None):
        """Saves the project to a JSON file

        Calls the function save_teaser_json in data.output.teaserjson_output

        Parameters
        ----------

        file_name : string
            name of the new file
        path : string
            if the Files should not be stored in OutputData, an alternative
            can be specified
        """
        if file_name is None:
            name = self.name
        else:
            name = file_name

        if path is None:
            new_path = os.path.join(utilities.get_default_path(), name)
        else:
            new_path = os.path.join(path, name)

        tjson_out.save_teaser_json(new_path, self)

    def load_project(self, path):
        """Load the project from a json file (new format).

        Calls the function load_teaser_json.

        Parameters
        ----------
        path : string
            full path to a json file

        """

        tjson_in.load_teaser_json(path, self)

    def export_aixlib(
            self,
            building_model=None,
            zone_model=None,
            corG=None,
            internal_id=None,
            path=None,
    ):
        """Exports values to a record file for Modelica simulation

        Exports one (if internal_id is not None) or all buildings for
        AixLib.ThermalZones.ReducedOrder.Multizone.MultizoneEquipped models
        using the ThermalZoneEquipped model with a correction of g-value (
        double pane glazing) and supporting models, like tables and weather
        model. In contrast to versions < 0.5 TEASER now does not
        support any model options, as we observed no need, since single
        ThermalZones are identically with IBPSA models. If you miss one of
        the old options please contact us.

        Parameters
        ----------

        internal_id : float
            setter of a specific building which will be exported, if None then
            all buildings will be exported
        path : string
            if the Files should not be stored in default output path of TEASER,
            an alternative path can be specified as a full path
        """

        if building_model is not None or zone_model is not None or corG is not None:
            warnings.warn(
                "building_model, zone_model and corG are no longer "
                "supported for AixLib export and have no effect. "
                "The keywords will be deleted within the next "
                "version, consider rewriting your code."
            )

        if path is None:
            path = os.path.join(utilities.get_default_path(), self.name)
        else:
            path = os.path.join(path, self.name)

        utilities.create_path(path)

        if internal_id is None:
            aixlib_output.export_multizone(
                buildings=self.buildings, prj=self, path=path
            )
        else:
            for bldg in self.buildings:
                if bldg.internal_id == internal_id:
                    aixlib_output.export_multizone(
                        buildings=[bldg], prj=self, path=path
                    )
        return path

    def export_ibpsa(self, library="AixLib", internal_id=None, path=None):
        """Exports values to a record file for Modelica simulation

        For Annex 60 Library

        Parameters
        ----------

        library : str
            Used library within the framework of IBPSA library. The
            models are identical in each library, but IBPSA Modelica library is
            just a core set of models and should not be used standalone.
            Valid values are 'AixLib' (default), 'Buildings',
            'BuildingSystems' and 'IDEAS'.
        internal_id : float
            setter of a specific building which will be exported, if None then
            all buildings will be exported
        path : string
            if the Files should not be stored in default output path of TEASER,
            an alternative path can be specified as a full path
        """

        ass_error_1 = (
            "library for IBPSA export has to be 'AixLib', "
            "'Buildings', 'BuildingSystems' or 'IDEAS'"
        )

        assert library in [
            "AixLib",
            "Buildings",
            "BuildingSystems",
            "IDEAS",
        ], ass_error_1

        if path is None:
            path = os.path.join(utilities.get_default_path(), self.name)
        else:
            path = os.path.join(path, self.name)

        utilities.create_path(path)

        if internal_id is None:
            ibpsa_output.export_ibpsa(
                buildings=self.buildings, prj=self, path=path, library=library
            )
        else:
            for bldg in self.buildings:
                if bldg.internal_id == internal_id:
                    ibpsa_output.export_ibpsa(buildings=[bldg], prj=self, path=path)
        return path

    def set_default(self, load_data=None):
        """Sets all attributes to default

        Caution: this will delete all buildings.

        Parameters
        ----------
        load_data : boolean, None-type
            boolean if data bindings for type elements and use conditions
            should be loaded (default = True), in addition it could be a None-
            type to use the already used data bindings
        """

        self._name = "Project"
        self.modelica_info = ModelicaInfo()

        self.weather_file_path = utilities.get_full_path(
            os.path.join(
                "data",
                "input",
                "inputdata",
                "weatherdata",
                "DEU_BW_Mannheim_107290_TRY2010_12_Jahr_BBSR.mos",
            )
        )

        self.buildings = []

        #TODO #745 hier vielleicht noch Anpassungen notwendig
        if load_data is True:
            self.data = self.instantiate_data_class()
        elif not load_data:
            pass
        else:
            self.data = None

        self._number_of_elements_calc = 2
        self._merge_windows_calc = False
        self._used_library_calc = "AixLib"

    @property
    def weather_file_path(self):
        return self._weather_file_path

    @weather_file_path.setter
    def weather_file_path(self, value):
        if value is None:
            self._weather_file_path = utilities.get_full_path(
                os.path.join(
                    "data",
                    "input",
                    "inputdata",
                    "weatherdata",
                    "DEU_BW_Mannheim_107290_TRY2010_12_Jahr_BBSR.mos",
                )
            )
        else:
            self._weather_file_path = os.path.normpath(value)
            self.weather_file_name = os.path.split(self.weather_file_path)[1]

    @property
    def number_of_elements_calc(self):
        return self._number_of_elements_calc

    @number_of_elements_calc.setter
    def number_of_elements_calc(self, value):

        ass_error_1 = "number_of_elements_calc has to be 1,2,3 or 4"

        assert value != [1, 2, 3, 4], ass_error_1

        self._number_of_elements_calc = value

        for bldg in self.buildings:
            bldg.number_of_elements_calc = value

    @property
    def merge_windows_calc(self):
        return self._merge_windows_calc

    @merge_windows_calc.setter
    def merge_windows_calc(self, value):

        ass_error_1 = "merge windows needs to be True or False"

        assert value != [True, False], ass_error_1

        self._merge_windows_calc = value

        for bldg in self.buildings:
            bldg.merge_windows_calc = value

    @property
    def used_library_calc(self):
        return self._used_library_calc

    @used_library_calc.setter
    def used_library_calc(self, value):

        ass_error_1 = "used library needs to be AixLib or IBPSA"

        assert value != ["AixLib", "IBPSA"], ass_error_1

        self._used_library_calc = value

        for bldg in self.buildings:
            bldg.used_library_calc = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, str):
            regex = re.compile("[^a-zA-z0-9]")
            self._name = regex.sub("", value)
        else:
            try:
                value = str(value)
                regex = re.compile("[^a-zA-z0-9]")
                self._name = regex.sub("", value)
            except ValueError:
                print("Can't convert name to string")

        if self._name[0].isdigit():
            self._name = "P" + self._name
