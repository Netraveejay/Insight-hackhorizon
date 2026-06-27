"""M365 Graph adapter STUB — production inbox/KPI/disruption source."""

from app.connectors.base import ProductionConnectorStub

GraphInboxConnector = ProductionConnectorStub("graph_inbox", "M365 Graph Inbox")
GraphKPIConnector = ProductionConnectorStub("graph_kpi", "M365 Graph KPI Emails")
GraphDisruptionConnector = ProductionConnectorStub("graph_disruption", "M365 Graph Disruption Notifications")
