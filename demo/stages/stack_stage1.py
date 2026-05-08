"""Stage 1: Base flight tracker — no AI feature, no CDK Nag."""
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

SECRET_NAME = "skywatch/api-keys"


class SkywatchStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # --- Configuration ---
        location = self.node.try_get_context("location") or "LGB"
        radius_km = int(self.node.try_get_context("radius_km") or "50")

        secret = secretsmanager.Secret.from_secret_name_v2(
            self, "ApiKeys", SECRET_NAME
        )

        # --- Storage ---
        flights_table = dynamodb.Table(
            self, "Flights",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # --- Shared Lambda config ---
        lambda_env = {
            "TABLE_NAME": flights_table.table_name,
            "LOCATION": location,
            "RADIUS_KM": str(radius_km),
            "SECRET_NAME": SECRET_NAME,
        }

        # --- Poller: fetches live flights from OpenSky ---
        poller = lambda_.Function(
            self, "Poller",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), "lambdas/poller")),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=lambda_env,
        )
        flights_table.grant_read_write_data(poller)
        secret.grant_read(poller)

        events.Rule(
            self, "PollSchedule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[targets.LambdaFunction(poller)],
        )

        # --- API: serves flight data to the frontend ---
        api_handler = lambda_.Function(
            self, "Api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname(__file__), "lambdas/api")),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=lambda_env,
        )
        flights_table.grant_read_write_data(api_handler)
        secret.grant_read(api_handler)

        api = apigw.HttpApi(
            self, "HttpApi",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.DELETE, apigw.CorsHttpMethod.OPTIONS],
                allow_headers=["Content-Type"],
            ),
        )
        api_integration = integrations.HttpLambdaIntegration("ApiIntegration", api_handler)
        api.add_routes(path="/flights", methods=[apigw.HttpMethod.GET], integration=api_integration)
        api.add_routes(path="/spotlight", methods=[apigw.HttpMethod.GET, apigw.HttpMethod.POST], integration=api_integration)
        api.add_routes(path="/community", methods=[apigw.HttpMethod.GET, apigw.HttpMethod.POST, apigw.HttpMethod.DELETE], integration=api_integration)
        api.add_routes(path="/flight/{callsign}", methods=[apigw.HttpMethod.GET], integration=api_integration)

        # --- Frontend: S3 + CloudFront ---
        site_bucket = s3.Bucket(
            self, "SiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        distribution = cloudfront.Distribution(
            self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
        )

        import boto3 as _boto3
        import json as _json
        _sm = _boto3.client("secretsmanager", region_name="us-east-1")
        _secrets = _json.loads(_sm.get_secret_value(SecretId=SECRET_NAME)["SecretString"])
        _mapbox_token = _secrets.get("MAPBOX_TOKEN", "")

        s3deploy.BucketDeployment(
            self, "DeploySite",
            sources=[
                s3deploy.Source.asset(os.path.join(os.path.dirname(__file__), "../frontend")),
                s3deploy.Source.data("config.js", f"window.SKYWATCH_CONFIG = {{ MAPBOX_TOKEN: '{_mapbox_token}' }};\n"),
            ],
            destination_bucket=site_bucket,
            distribution=distribution,
        )

        # --- Outputs ---
        cdk.CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        cdk.CfnOutput(self, "ApiUrl", value=api.url or "")
