"""
Auditor Agent MCP Server

Wraps the AuditorAgent in an MCP server for distributed processing
Exposes audit and compliance operations as MCP tools
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from .base_mcp_server import BaseMCPServer, MCPServerConfig
from .utils import log_operation

# Import the existing AuditorAgent
import sys
sys.path.insert(0, '../agents')
from auditor_agent import AuditorAgent

logger = logging.getLogger(__name__)


class AuditorMCPServer(BaseMCPServer):
    """
    MCP server for Auditor Agent
    Provides distributed audit and compliance capabilities
    """

    def __init__(self, config: Optional[MCPServerConfig] = None):
        """Initialize Auditor MCP server"""
        if config is None:
            config = MCPServerConfig(
                name="Auditor MCP Server",
                description="Audit and compliance system",
                version="1.0.0",
                port=8005
            )
        
        super().__init__(config)
        self.agent: Optional[AuditorAgent] = None

    async def initialize(self) -> None:
        """Initialize auditor agent and register tools"""
        logger.info("Initializing Auditor Agent...")
        
        # Initialize the agent
        self.agent = AuditorAgent()
        
        # Register tools that expose agent methods
        await self._register_tools()
        
        logger.info("Auditor Agent initialized successfully")

    async def _register_tools(self) -> None:
        """Register audit tools"""
        
        # Audit Activity
        self.register_tool(
            name="audit_activity",
            description="Audit system activity and generate report",
            handler=self._audit_activity,
            input_schema={
                "properties": {
                    "start_time": {"type": "string", "description": "Start time (ISO format)"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "activity_type": {"type": "string", "description": "Type of activity to audit"},
                    "user_id": {"type": "string", "description": "Specific user to audit"}
                }
            },
            required_fields=["start_time", "end_time"]
        )
        
        # Check Compliance
        self.register_tool(
            name="check_compliance",
            description="Check compliance with policies and regulations",
            handler=self._check_compliance,
            input_schema={
                "properties": {
                    "policy": {"type": "string", "description": "Policy to check"},
                    "scope": {"type": "string", "description": "Scope of compliance check"},
                    "severity": {"type": "string", "enum": ["all", "critical", "high"]}
                }
            },
            required_fields=["policy"]
        )
        
        # Generate Report
        self.register_tool(
            name="generate_report",
            description="Generate audit report",
            handler=self._generate_report,
            input_schema={
                "properties": {
                    "report_type": {"type": "string", "description": "Type of report"},
                    "start_date": {"type": "string", "description": "Report start date"},
                    "end_date": {"type": "string", "description": "Report end date"},
                    "format": {"type": "string", "enum": ["json", "pdf", "csv"]}
                }
            },
            required_fields=["report_type"]
        )
        
        # Log Access
        self.register_tool(
            name="log_access",
            description="Log data access for audit trail",
            handler=self._log_access,
            input_schema={
                "properties": {
                    "resource_id": {"type": "string", "description": "Resource accessed"},
                    "user_id": {"type": "string", "description": "User accessing resource"},
                    "access_type": {"type": "string", "enum": ["read", "write", "delete"]},
                    "metadata": {"type": "object", "description": "Additional metadata"}
                }
            },
            required_fields=["resource_id", "user_id", "access_type"]
        )
        
        # Verify Integrity
        self.register_tool(
            name="verify_integrity",
            description="Verify data integrity and consistency",
            handler=self._verify_integrity,
            input_schema={
                "properties": {
                    "data_id": {"type": "string", "description": "Data to verify"},
                    "check_type": {"type": "string", "description": "Type of integrity check"}
                }
            },
            required_fields=["data_id"]
        )
        
        # Flag Anomaly
        self.register_tool(
            name="flag_anomaly",
            description="Flag unusual system behavior",
            handler=self._flag_anomaly,
            input_schema={
                "properties": {
                    "anomaly_type": {"type": "string", "description": "Type of anomaly"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "description": {"type": "string", "description": "Description of anomaly"},
                    "context": {"type": "object", "description": "Context information"}
                }
            },
            required_fields=["anomaly_type"]
        )

    async def _audit_activity(self, start_time: str, end_time: str, activity_type: str = None,
                             user_id: str = None) -> Dict[str, Any]:
        """Audit system activity"""
        try:
            log_operation("audit_activity", self.config.name, "started",
                         {"start": start_time, "end": end_time})
            
            audit_report = await self.agent.audit_activity(
                start_time=start_time,
                end_time=end_time,
                activity_type=activity_type,
                user_id=user_id
            )
            
            log_operation("audit_activity", self.config.name, "completed", {})
            return audit_report
            
        except Exception as e:
            logger.error(f"Error auditing activity: {e}")
            self.log_error(e, {"operation": "audit_activity"})
            raise

    async def _check_compliance(self, policy: str, scope: str = None,
                               severity: str = "all") -> Dict[str, Any]:
        """Check compliance"""
        try:
            log_operation("check_compliance", self.config.name, "started", {"policy": policy})
            
            compliance_report = await self.agent.check_compliance(
                policy=policy,
                scope=scope or "all",
                severity=severity
            )
            
            log_operation("check_compliance", self.config.name, "completed", {})
            return compliance_report
            
        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            self.log_error(e, {"operation": "check_compliance"})
            raise

    async def _generate_report(self, report_type: str, start_date: str = None,
                              end_date: str = None, format: str = "json") -> Dict[str, Any]:
        """Generate audit report"""
        try:
            log_operation("generate_report", self.config.name, "started", {"type": report_type})
            
            report = await self.agent.generate_report(
                report_type=report_type,
                start_date=start_date,
                end_date=end_date,
                format=format
            )
            
            log_operation("generate_report", self.config.name, "completed", {})
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            self.log_error(e, {"operation": "generate_report"})
            raise

    async def _log_access(self, resource_id: str, user_id: str, access_type: str,
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Log access"""
        try:
            log_operation("log_access", self.config.name, "started",
                         {"resource": resource_id, "user": user_id})
            
            access_log = await self.agent.log_access(
                resource_id=resource_id,
                user_id=user_id,
                access_type=access_type,
                metadata=metadata or {}
            )
            
            log_operation("log_access", self.config.name, "completed", {})
            return access_log
            
        except Exception as e:
            logger.error(f"Error logging access: {e}")
            self.log_error(e, {"operation": "log_access"})
            raise

    async def _verify_integrity(self, data_id: str, check_type: str = "full") -> Dict[str, Any]:
        """Verify integrity"""
        try:
            log_operation("verify_integrity", self.config.name, "started", {"data_id": data_id})
            
            integrity_result = await self.agent.verify_integrity(
                data_id=data_id,
                check_type=check_type
            )
            
            log_operation("verify_integrity", self.config.name, "completed", {})
            return integrity_result
            
        except Exception as e:
            logger.error(f"Error verifying integrity: {e}")
            self.log_error(e, {"operation": "verify_integrity"})
            raise

    async def _flag_anomaly(self, anomaly_type: str, severity: str = "medium",
                           description: str = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Flag anomaly"""
        try:
            log_operation("flag_anomaly", self.config.name, "started",
                         {"type": anomaly_type, "severity": severity})
            
            anomaly_flag = await self.agent.flag_anomaly(
                anomaly_type=anomaly_type,
                severity=severity,
                description=description or "",
                context=context or {}
            )
            
            log_operation("flag_anomaly", self.config.name, "completed", {})
            return anomaly_flag
            
        except Exception as e:
            logger.error(f"Error flagging anomaly: {e}")
            self.log_error(e, {"operation": "flag_anomaly"})
            raise


async def create_and_start_auditor_server(port: int = 8005) -> AuditorMCPServer:
    """
    Factory function to create and start Auditor MCP server
    
    Args:
        port: Port to run server on
        
    Returns:
        Started AuditorMCPServer instance
    """
    config = MCPServerConfig(
        name="Auditor MCP Server",
        description="Audit and compliance via MCP",
        version="1.0.0",
        port=port
    )
    
    server = AuditorMCPServer(config)
    await server.initialize()
    await server.start(port)
    
    return server


if __name__ == "__main__":
    # For local testing
    import asyncio
    
    async def main():
        server = await create_and_start_auditor_server()
        print(f"Auditor MCP Server running on port {server.config.port}")
        print(f"Available tools: {len(server.list_tools())}")
        for tool in server.list_tools():
            print(f"  - {tool['name']}: {tool['description']}")
    
    asyncio.run(main())
