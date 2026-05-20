from decimal import Decimal, InvalidOperation
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from utils.connectionMongo import MongoDBConnectionSingleton
from utils.logger import SingletonLogger


TASK_COLLECTION = "System_tasks"
TASK_INPROGRESS_COLLECTION = "System_tasks_Inprogress"
INCIDENT_COLLECTION = "Incident"
SEQUENCE_COLLECTION = "collection_sequence"
TASK_ID_SEQUENCE_KEY = "incident_arrears_mismatch_task_id"
TEMPLATE_TASK_ID = 200
TASK_TYPE = "Create Task for Arrears Mismatch Case List"


def _to_decimal(value):
	if value is None:
		return None
	try:
		return Decimal(str(value).strip())
	except (InvalidOperation, ValueError, TypeError):
		return None


def _find_mismatch_incidents(database):
	incident_collection = database[INCIDENT_COLLECTION]
	cursor = incident_collection.find(
		{"Incident_Status": "Open"},
		{
			"Incident_Id": 1,
			"Arrears": 1,
			"Bss_Arrears_Amount": 1,
			"Incident_Status": 1,
		},
	)

	mismatches = []
	for doc in cursor:
		incident_id = doc.get("Incident_Id")
		arrears = _to_decimal(doc.get("Arrears"))
		bss_arrears = _to_decimal(doc.get("Bss_Arrears_Amount"))

		if incident_id is None:
			continue
		if arrears is None or bss_arrears is None:
			continue
		if arrears != bss_arrears:
			mismatches.append(
				{
					"Incident_Id": incident_id,
					"Arrears": float(arrears),
					"Bss_Arrears_Amount": float(bss_arrears),
				}
			)

	return mismatches


def _get_next_task_id(database):
	"""
	Safely get the next Task_Id using MongoDB atomic counter.
	Uses findOneAndUpdate with $inc to ensure no concurrent ID collisions.
	"""
	sequence_collection = database[SEQUENCE_COLLECTION]
	sequence_doc = sequence_collection.find_one_and_update(
		{"_id": TASK_ID_SEQUENCE_KEY},
		{"$inc": {"seq": 1}},
		upsert=True,
		return_document=ReturnDocument.AFTER,
	)
	return sequence_doc.get("seq", 1)


def _ensure_task_id_sequence(database):
	"""
	Initialize sequence from existing tasks if sequence document is missing.
	"""
	sequence_collection = database[SEQUENCE_COLLECTION]
	existing_sequence = sequence_collection.find_one({"_id": TASK_ID_SEQUENCE_KEY})

	if existing_sequence is not None:
		return

	# First time: find max Task_Id from both collections.
	max_task = None
	for collection_name in (TASK_COLLECTION, TASK_INPROGRESS_COLLECTION):
		collection = database[collection_name]
		document = collection.find_one(
			{},
			sort=[("Task_Id", -1)],
			projection={"Task_Id": 1},
		)
		if document and isinstance(document.get("Task_Id"), int):
			if max_task is None or document["Task_Id"] > max_task:
				max_task = document["Task_Id"]

	# Initialize sequence with the current max so next increment returns max + 1.
	start_value = max_task if max_task is not None else 0
	try:
		sequence_collection.insert_one({"_id": TASK_ID_SEQUENCE_KEY, "seq": start_value})
	except DuplicateKeyError:
		# Another process may initialize it at the same time.
		pass


def _task_exists(database, incident_id):
	for collection_name in (TASK_COLLECTION, TASK_INPROGRESS_COLLECTION):
		collection = database[collection_name]
		if collection.find_one(
			{
				"Incident_Id": incident_id,
				"Template_Task_Id": TEMPLATE_TASK_ID,
			},
			projection={"_id": 1},
		) is not None:
			return True
	return False


def _build_task_document(next_task_id, incident_id):
	return {
		"Task_Id": next_task_id,
		"Template_Task_Id": TEMPLATE_TASK_ID,
		"Task_Type": TASK_TYPE,
		"Incident_Id": incident_id,
	}


def create_arrears_mismatch_tasks(database):
	task_collection = database[TASK_COLLECTION]
	progress_collection = database[TASK_INPROGRESS_COLLECTION]
	mismatch_incidents = _find_mismatch_incidents(database)
	_ensure_task_id_sequence(database)

	created_count = 0
	skipped_existing = 0
	task_count = 0
	progress_count = 0

	for item in mismatch_incidents:
		incident_id = item["Incident_Id"]

		if _task_exists(database, incident_id):
			skipped_existing += 1
			continue

		next_task_id = _get_next_task_id(database)

		task_doc = _build_task_document(next_task_id, incident_id)
		progress_doc = _build_task_document(next_task_id, incident_id)
		
		# Update or insert into System_tasks
		task_result = task_collection.update_one(
			{
				"Task_Id": next_task_id,
				"Template_Task_Id": TEMPLATE_TASK_ID,
				"Incident_Id": incident_id,
			},
			{"$set": task_doc},
			upsert=True,
		)
		if task_result.upserted_id is not None or task_result.modified_count > 0:
			task_count += 1
		
		# Update or insert into System_tasks_Inprogress
		progress_result = progress_collection.update_one(
			{
				"Task_Id": next_task_id,
				"Template_Task_Id": TEMPLATE_TASK_ID,
				"Incident_Id": incident_id,
			},
			{"$set": progress_doc},
			upsert=True,
		)
		if progress_result.upserted_id is not None or progress_result.modified_count > 0:
			progress_count += 1
		created_count += 1

	return {
		"mismatch_count": len(mismatch_incidents),
		"created_count": created_count,
		"skipped_existing": skipped_existing,
		"task_count": task_count,
		"progress_count": progress_count,
	}


def run_arrears_mismatch_task_creator():
	SingletonLogger.configure()
	logger = SingletonLogger.get_logger("appLogger")

	client = MongoDBConnectionSingleton.get_instance()
	database = client.get_database()

	if database is None:
		raise RuntimeError("MongoDB database is not available")

	result = create_arrears_mismatch_tasks(database)
	logger.info(
		"Arrears mismatch task creator done. mismatch_count=%s created_count=%s skipped_existing=%s task_count=%s progress_count=%s",
		result["mismatch_count"],
		result["created_count"],
		result["skipped_existing"],
		result["task_count"],
		result["progress_count"],
	)
	print(
		"✓ Arrears mismatch check completed | "
		f"mismatch: {result['mismatch_count']} | "
		f"created: {result['created_count']} | "
		f"already_exists: {result['skipped_existing']} | "
		f"task_updated: {result['task_count']} | "
		f"progress_updated: {result['progress_count']}"
	)

	return result


if __name__ == "__main__":
	run_arrears_mismatch_task_creator()
