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
    import os

    max_number_items_fNtx = 15
    tui_logging = None
    Configs.load_config()

    KnownErrors.configs = Configs
    KnownErrors.initialize()
    data_dir = Configs.get_config_for('FILE_SETUP.CONFIG.data_dir')

    app_path =f"{os.path.dirname(os.path.abspath(__file__))}/{data_dir}"

    # 1. Configurar archivo
    file_to_analyse = FileManagement(log_file_path, block_size_in_mb=15)
    if not file_to_analyse.state:
        raise ValueError("Invalid log file")

    file_to_analyse.discover_file_format()

    # 2. Extraer bloques especiales (opcional, si los necesitas en la API)
    special_blocks = BlockExtractor(file_to_analyse, Configs.config)
    special_blocks.extract()

    # 3. Configurar recolectores
    collect_parties = GetParties(Configs)
    collect_parties.set_file(file_to_analyse)
    collect_parties.set_element_type(CordaObject.Type.PARTY)

    collect_refIds = GetRefIds(Configs)
    collect_refIds.set_file(file_to_analyse)
    collect_refIds.set_element_type(CordaObject.Type.FLOW_AND_TRANSACTIONS)

    # 4. Ejecutar procesamiento
    file_to_analyse.pre_analysis()
    file_to_analyse.add_process_to_execute(collect_parties)
    file_to_analyse.add_process_to_execute(collect_refIds)
    file_to_analyse.parallel_processing()

    # 1. Obtener todos los roles detectados en el log
    detected_roles = file_to_analyse.get_party_role()

    # Si quieres soportar múltiples roles por party:
    x500_to_roles = {}
    for role in detected_roles:
        for x500 in (file_to_analyse.get_party_role(role) or []):
            x500_to_roles.setdefault(x500, []).append(role)

    # Luego:
    parties = [
        {"name": p.name, "roles": x500_to_roles.get(p.name, [])}
        for p in file_to_analyse.get_all_unique_results(CordaObject.Type.PARTY, True) or []
    ]

    flows = []
    transactions = []
    for item in file_to_analyse.get_all_unique_results(CordaObject.Type.FLOW_AND_TRANSACTIONS, True) or []:
        ref_id = item.get_reference_id()
        if item.get_type() == "FLOW":
            flows.append(ref_id)
        elif item.get_type() == "TRANSACTION":
            transactions.append(ref_id)

    # 6. Devolver resultado estructurado
    return {
        "summary": {
            "total_parties": len(parties),
            "total_flows": len(flows),
            "total_transactions": len(transactions),
        },
        "parties": parties,
        "flows": flows,
        "transactions": transactions,
        # Puedes añadir "delays", "special_blocks", etc. si los expones
    }