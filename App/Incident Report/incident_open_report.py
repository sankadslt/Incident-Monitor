from datetime import datetime
import os
from utils.api_client import send_email_api
from utils.connectionMongo import MongoDBConnectionSingleton
from utils.logger import SingletonLogger
from utils.urlpath import SingletonUrlPath

def fetch_open_incidents(db):
    """
    Fetch open incidents from the database and group them by:
    - Incident_Status_Dtm
    - Drc_Commision_Rule
    - Incident_direction

    Args:
        db: MongoDB database instance from MongoDBConnectionSingleton

    Returns:
        list: Grouped incidents with count of each group
    """
    try:
        incidents_collection = db["Incident"]

        pipeline = [
            {
                "$match": {"Incident_Status": "Open"}
            },
            {
                "$group": {
                    "_id": {
                        "Created_Dtm": "$Created_Dtm",
                        "Drc_Commision_Rule": "$Drc_Commision_Rule",
                        "Incident_direction": "$Incident_direction",
                    },
                    "count": {"$sum": 1},
                }
            },
            {
                "$sort": {"_id.Created_Dtm": -1}
            },
        ]

        results = list(incidents_collection.aggregate(pipeline))

        grouped_data = []
        for result in results:
            grouped_data.append(
                {
                    "Created_Dtm": result["_id"]["Created_Dtm"],
                    "Drc_Commision_Rule": result["_id"]["Drc_Commision_Rule"],
                    "Incident_direction": result["_id"]["Incident_direction"],
                    "count": result["count"],
                }
            )

        print(f"✓ Fetched {len(grouped_data)} incident groups")
        return grouped_data

    except Exception as e:
        print(f"✗ Error fetching open incidents: {str(e)}")
        raise

def build_table_data(data):
    table_data = []
    print(f"[DEBUG BUILD_TABLE] Processing {len(data)} rows")

    for idx, row in enumerate(data):
        print(f"[DEBUG BUILD_TABLE] Row {idx}: {row}")
        created_dtm = row["Created_Dtm"]
        if isinstance(created_dtm, datetime):
            created_dtm = created_dtm.strftime("%Y-%m-%d")
        else:
            created_dtm = str(created_dtm)[:10]

        table_data.append(
            {
                "Created_Dtm": created_dtm,
                "Drc_Commision_Rule": row["Drc_Commision_Rule"],
                "Incident_direction": row["Incident_direction"],
                "count": row["count"],
            }
        )

    print(f"[DEBUG BUILD_TABLE] Built {len(table_data)} rows: {table_data}")
    return table_data

def build_payload(table_data, email_api_url, recipient_mail, cc_recipients):
    return {
        "template_id": 31,
        "Subject": "Incident Open Report",
        "RecieverMail": recipient_mail,
        "CarbonCopyTo": cc_recipients,
        "DeliveryMode": "api",
        "ConfiguredEmailApiUrl": email_api_url,
        "EmailBody": {
            "Subject": "Incident Open Report",
            "Reciever_Name": "Nishantha",
            "table": table_data,
        },
    }

def run_incident_summary():
    SingletonLogger.configure()
    logger = SingletonLogger.get_logger("appLogger")

    SingletonUrlPath.configure()
    email_api_url = SingletonUrlPath.get().get_email_api_url()

    logger.info("Running incident summary in local log mode")
    logger.info("Configured EMAIL_API_URL: %s", email_api_url)

    client = MongoDBConnectionSingleton.get_instance()
    database = client.get_database()

    if database is None:
        raise RuntimeError("MongoDB database is not available")

    data = fetch_open_incidents(database)
    
    # Only process if there are incidents to report
    if not data:
        logger.info("No open incidents found")
        print("✓ No open incidents to report")
        return {
            "status": "no_data",
            "file": None,
            "reason": "No open incidents in the database"
        }
    
    table_data = build_table_data(data)
    recipient_mail = os.getenv("EMAIL_RECIPIENT", os.getenv("EMAIL_USER", "nish@slt.com.lk")).strip()
    cc_raw = os.getenv("EMAIL_CC", "").strip()
    cc_recipients = [item.strip() for item in cc_raw.split(",") if item.strip()]

    payload = build_payload(table_data, email_api_url, recipient_mail, cc_recipients)

    result = send_email_api(payload)
    
    if result.get("status") in {"sent", "processing", "queued"}:
        logger.info("Incident summary email request completed: %s", result.get("response", result.get("details")))
        print("✓ Incident summary email request completed")
    else:
        logger.info("Incident summary skipped: %s", result.get("reason"))
        print(f"✓ Incident summary skipped: {result.get('reason')}")
    
    return result

if __name__ == "__main__":
    run_incident_summary()
