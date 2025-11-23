from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class CDKGenerator:
    """Generate AWS CDK templates from requirements"""
    
    def __init__(self):
        pass
    
    async def generate(self, project_name: str, requirements: Dict[str, Any], optimization_level: str = "balanced") -> str:
        """Generate CDK TypeScript template"""
        try:
            project_name = self._sanitize_name(project_name)
            
            # Generate CDK app structure
            template = f'''import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import {{ Construct }} from 'constructs';

export class {self._to_pascal_case(project_name)}Stack extends cdk.Stack {{
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {{
    super(scope, id, props);

    // VPC
    const vpc = new ec2.Vpc(this, 'VPC', {{
      maxAzs: 2,
      natGateways: 1,
      cidr: '10.0.0.0/16',
      subnetConfiguration: [
        {{
          cidrMask: 24,
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
        }},
        {{
          cidrMask: 24,
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }},
      ],
    }});
'''

            # Add compute resources
            if requirements.get("compute"):
                template += self._add_compute_resources(requirements["compute"])
            
            # Add database resources
            if requirements.get("database"):
                template += self._add_database_resources(requirements["database"])
            
            # Add cache resources
            if requirements.get("cache"):
                template += self._add_cache_resources(requirements["cache"])
            
            # Add storage resources
            if requirements.get("storage"):
                template += self._add_storage_resources(requirements["storage"])
            
            # Close the class
            template += '''
  }
}

// CDK App
const app = new cdk.App();
new ''' + self._to_pascal_case(project_name) + '''Stack(app, '''' + self._to_pascal_case(project_name) + '''Stack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2',
  },
});
'''
            
            return template
            
        except Exception as e:
            logger.error(f"CDK generation error: {e}")
            return self._generate_fallback_template(project_name, requirements)
    
    def _add_compute_resources(self, compute: Dict[str, Any]) -> str:
        """Add compute resources to CDK template"""
        compute_type = compute.get("type", "container")
        
        if compute_type == "container":
            cpu = int(float(compute.get("cpu", "0.25")) * 1024)  # Convert to CDK CPU units
            memory = self._parse_memory_mb(compute.get("memory", "512Mi"))
            
            return f'''
    // ECS Cluster
    const cluster = new ecs.Cluster(this, 'Cluster', {{
      vpc,
      containerInsights: true,
    }});

    // Fargate Service
    const fargateService = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'FargateService', {{
      cluster,
      cpu: {cpu},
      memoryLimitMiB: {memory},
      desiredCount: {compute.get("replicas", 1)},
      taskImageOptions: {{
        image: ecs.ContainerImage.fromRegistry('nginx:latest'),
        containerPort: 80,
      }},
      publicLoadBalancer: true,
    }});

    // Auto Scaling
    const scaling = fargateService.service.autoScaleTaskCount({{
      minCapacity: 1,
      maxCapacity: {compute.get("max_replicas", 10)},
    }});

    scaling.scaleOnCpuUtilization('CpuScaling', {{
      targetUtilizationPercent: 70,
    }});
'''
        
        elif compute_type == "lambda":
            memory = compute.get("memory", 128)
            timeout = compute.get("timeout", 30)
            
            return f'''
    // Lambda Function
    const lambdaFunction = new lambda.Function(this, 'Function', {{
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
def handler(event, context):
    return {{
        'statusCode': 200,
        'body': 'Hello from Lambda!'
    }}
`),
      memorySize: {memory},
      timeout: cdk.Duration.seconds({timeout}),
    }});
'''
        
        return ""
    
    def _add_database_resources(self, database: Dict[str, Any]) -> str:
        """Add database resources to CDK template"""
        db_type = database.get("type", "postgresql")
        instance_class = database.get("size", "db.t3.micro")
        
        engine_map = {
            "postgresql": "rds.DatabaseInstanceEngine.postgres",
            "mysql": "rds.DatabaseInstanceEngine.mysql",
            "mariadb": "rds.DatabaseInstanceEngine.mariaDb"
        }
        
        engine = engine_map.get(db_type, "rds.DatabaseInstanceEngine.postgres")
        
        return f'''
    // RDS Database
    const database = new rds.DatabaseInstance(this, 'Database', {{
      engine: {engine}({{
        version: {self._get_cdk_db_version(db_type)},
      }}),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      vpc,
      vpcSubnets: {{
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      }},
      multiAz: false,
      allocatedStorage: 20,
      storageEncrypted: true,
      deletionProtection: false,
      databaseName: 'appdb',
      credentials: rds.Credentials.fromGeneratedSecret('admin'),
      backupRetention: cdk.Duration.days(7),
      deleteAutomatedBackups: true,
    }});
'''
    
    def _add_cache_resources(self, cache: Dict[str, Any]) -> str:
        """Add cache resources to CDK template"""
        return '''
    // ElastiCache Redis
    const subnetGroup = new elasticache.CfnSubnetGroup(this, 'CacheSubnetGroup', {
      description: 'Subnet group for ElastiCache',
      subnetIds: vpc.privateSubnets.map(subnet => subnet.subnetId),
    });

    const securityGroup = new ec2.SecurityGroup(this, 'CacheSecurityGroup', {
      vpc,
      description: 'Security group for ElastiCache',
      allowAllOutbound: false,
    });

    securityGroup.addIngressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(6379),
      'Allow Redis access from VPC'
    );

    const cache = new elasticache.CfnReplicationGroup(this, 'Cache', {
      replicationGroupDescription: 'Redis cache',
      numCacheClusters: 1,
      cacheNodeType: 'cache.t3.micro',
      engine: 'redis',
      cacheSubnetGroupName: subnetGroup.ref,
      securityGroupIds: [securityGroup.securityGroupId],
      atRestEncryptionEnabled: true,
      transitEncryptionEnabled: true,
    });
'''
    
    def _add_storage_resources(self, storage: Dict[str, Any]) -> str:
        """Add storage resources to CDK template"""
        return '''
    // S3 Bucket
    const bucket = new s3.Bucket(this, 'StorageBucket', {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
'''
    
    def _generate_fallback_template(self, project_name: str, requirements: Dict[str, Any]) -> str:
        """Generate basic CDK template as fallback"""
        return f'''import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import {{ Construct }} from 'constructs';

export class {self._to_pascal_case(project_name)}Stack extends cdk.Stack {{
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {{
    super(scope, id, props);

    // Basic VPC
    const vpc = new ec2.Vpc(this, 'VPC', {{
      maxAzs: 2,
      natGateways: 1,
    }});

    // Output VPC ID
    new cdk.CfnOutput(this, 'VpcId', {{
      value: vpc.vpcId,
      description: 'VPC ID',
    }});
  }}
}}

const app = new cdk.App();
new {self._to_pascal_case(project_name)}Stack(app, '{self._to_pascal_case(project_name)}Stack');
'''
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for CDK"""
        import re
        # Replace invalid characters with hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9-]', '-', name)
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        return sanitized[:50]
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase"""
        return ''.join(word.capitalize() for word in name.replace('-', ' ').replace('_', ' ').split())
    
    def _parse_memory_mb(self, memory_str: str) -> int:
        """Parse memory string to MB"""
        if memory_str.endswith("Mi"):
            return int(memory_str[:-2])
        elif memory_str.endswith("Gi"):
            return int(memory_str[:-2]) * 1024
        elif memory_str.endswith("MB"):
            return int(memory_str[:-2])
        elif memory_str.endswith("GB"):
            return int(memory_str[:-2]) * 1024
        else:
            return int(memory_str)
    
    def _get_cdk_db_version(self, db_type: str) -> str:
        """Get CDK database version"""
        versions = {
            "postgresql": "rds.PostgresEngineVersion.VER_14_9",
            "mysql": "rds.MysqlEngineVersion.VER_8_0",
            "mariadb": "rds.MariaDbEngineVersion.VER_10_6"
        }
        return versions.get(db_type, "rds.PostgresEngineVersion.VER_14_9")