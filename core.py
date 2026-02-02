# logtracer/core.py


def analyze_corda_log(log_file_path: str) -> dict:
    """
    Analiza un archivo de log de Corda y devuelve un diccionario con:
    - parties
    - flows
    - transactions
    - estadísticas (tiempo, conteos, etc.)
    """
    from object_class import FileManagement
    from object_class import BlockExtractor
    from get_parties import GetParties
    from get_refIds import GetRefIds
    from object_class import CordaObject
    from object_class import Configs  # o pásalo como parámetro
    from object_class import KnownErrors
    from error_log_analysis import ErrorAnalisys
    import os

def analyze_corda_log(log_file_path: str, what_to_collect:CordaObject.Type=None) -> dict:
    """
    Analiza un archivo de log de Corda y devuelve un diccionario con:
    - parties
    - flows
    - transactions
    - estadísticas (tiempo, conteos, etc.)
    """

    max_number_items_fNtx = 15
    tui_logging = None
    Configs.load_config()
    payload = {
        "summary":{}
    }
    KnownErrors.configs = Configs
    KnownErrors.initialize()
    data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')

    app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

    # 1. Configurar archivo
    file_to_analyse = FileManagement(log_file_path, block_size_in_mb=15)

    if not file_to_analyse.state:
        raise ValueError(f"Unable to to read given file due to: {file_to_analyse.state_message}")

    file_to_analyse.discover_file_format()
    special_blocks = None
    collect_parties = None
    collect_refIds = None
    collect_errors = None

    if not what_to_collect or what_to_collect == CordaObject.Type.SPECIAL_BLOCKS:
        # 2. Extraer bloques especiales (opcional, si los necesitas en la API)
        special_blocks = BlockExtractor(file_to_analyse, Configs.config)
        special_blocks.extract()

    if not what_to_collect or what_to_collect == CordaObject.Type.PARTY:
        # 3. Configurar recolectores
        #
        # Party collection
        collect_parties = GetParties(Configs)
        collect_parties.set_file(file_to_analyse)
        collect_parties.set_element_type(CordaObject.Type.PARTY)
        file_to_analyse.add_process_to_execute(collect_parties)

    if not what_to_collect or what_to_collect == CordaObject.Type.FLOW_AND_TRANSACTIONS:
        #
        # Transactions and Flows collection
        collect_refIds = GetRefIds(Configs)
        collect_refIds.set_file(file_to_analyse)
        collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)
        file_to_analyse.add_process_to_execute(collect_refIds)

    if not what_to_collect or what_to_collect == CordaObject.Type.ERROR_ANALYSIS:
        #
        # Collection of Errors
        collect_errors = ErrorAnalisys(file_to_analyse, Configs.config)
        collect_errors.set_element_type(CordaObject.Type.ERROR_ANALYSIS)
        file_to_analyse.add_process_to_execute(collect_errors)

    # 4. Ejecutar procesamiento
    file_to_analyse.pre_analysis()
    # file_to_analyse.add_process_to_execute(collect_parties)
    # file_to_analyse.add_process_to_execute(collect_refIds)
    file_to_analyse.add_process_to_execute(collect_errors)
    file_to_analyse.parallel_processing()


    # Si quieres soportar múltiples roles por party:
    if collect_parties:
        # 1. Obtener todos los roles detectados en el log
        detected_roles = file_to_analyse.get_party_role()

        x500_to_roles = {}
        for role in detected_roles:
            for x500 in (file_to_analyse.get_party_role(role) or []):
                x500_to_roles.setdefault(x500, []).append(role)

        # Luego:
        parties = [
            {"name": p.type, "roles": x500_to_roles.get(p.type, [])}
            for p in file_to_analyse.get_all_unique_results(CordaObject.Type.PARTY, True) or []
        ]
        payload["summary"]["total_parties"] = len(parties)
        payload["summary"]["detected_roles"] = detected_roles
        payload["parties"] = parties

    if collect_refIds:
        flows = []
        transactions = []
        for item in file_to_analyse.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS, True) or []:
            ref_id = item.get_reference_id()
            if item.get_type() == "FLOW":
                flows.append(ref_id)
            elif item.get_type() == "TRANSACTION":
                transactions.append(ref_id)

        payload["summary"]["total_transactions"] = len(transactions)
        payload["summary"]["total_flows"]= len(flows)

        payload["flows"] = flows
        payload["transactions"] = transactions

    if special_blocks and  special_blocks.collected_blocks:
        payload["specialblocks"] = {
            "collected_blocktypes_types": special_blocks.get_collected_block_types(),
            "defined_blocktypes": special_blocks.get_defined_block_types(),
            "collected_blocktypes": special_blocks.get_all_content()
        }

    if collect_errors:
        collect_errors.collected_errors = file_to_analyse.get_all_unique_results(CordaObject.Type.ERROR_ANALYSIS)
        # payload["Error-log"] = collect_errors.get_error_category()
        payload['Error-Log'] = collect_errors.get_all_content()
        payload['summary'] = {
            'Error-log': collect_errors.get_error_summary()
        }

    # 6. Devolver resultado estructurado
    return payload
