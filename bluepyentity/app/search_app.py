import click
import bluepyentity
from bluepyentity.app.search.nexus_search import NexusSearch


@click.command()
@click.pass_context
def app(ctx):
    bucket = ctx.meta["bucket"]
    user = ctx.meta["user"]
    env = ctx.meta["env"]
    token = bluepyentity.token.get_token(env=env, username=user)
    app = NexusSearch(css_path="search.scss",
                      bucket=bucket,
                      token=token)
    app.run()

# app = NexusSearch(css_path='search.scss',
#                   bucket="bbp/hippocampus",
#                   token="eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI5T0R3Z1JSTFVsTTJHbFphVDZjVklnenJsb0lzUWJmbTBDck1icXNjNHQ4In0.eyJleHAiOjE2ODA3MDkyOTcsImlhdCI6MTY4MDY4MDQ5NywiYXV0aF90aW1lIjoxNjgwNjc2MTcwLCJqdGkiOiI3MzQwMGZjMi0wNzNjLTQ4OGItODBiOS05YWUxMTU0ZjRlMDUiLCJpc3MiOiJodHRwczovL2JicGF1dGguZXBmbC5jaC9hdXRoL3JlYWxtcy9CQlAiLCJhdWQiOlsiaHR0cHM6Ly9zbGFjay5jb20iLCJjb3Jlc2VydmljZXMtZ2l0bGFiIiwiYWNjb3VudCJdLCJzdWIiOiJmOjBmZGFkZWY3LWIyYjktNDkyYi1hZjQ2LWM2NTQ5MmQ0NTljMjpjb3VyY29sIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiYmJwLW5pc2UtbmV4dXMtZnVzaW9uIiwibm9uY2UiOiIxOWU4Y2U3OWYzZWU0NTJiYWNmNjRjZTdhMTc2NTNmYyIsInNlc3Npb25fc3RhdGUiOiI3ODJhNTA0Yi1hZGRiLTQ2NjAtOWU5ZC1kNDlmOGI0ODAyOWIiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiYmJwLXBhbS1hdXRoZW50aWNhdGlvbiIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iLCJkZWZhdWx0LXJvbGVzLWJicCJdfSwicmVzb3VyY2VfYWNjZXNzIjp7Imh0dHBzOi8vc2xhY2suY29tIjp7InJvbGVzIjpbInJlc3RyaWN0ZWQtYWNjZXNzIl19LCJjb3Jlc2VydmljZXMtZ2l0bGFiIjp7InJvbGVzIjpbInJlc3RyaWN0ZWQtYWNjZXNzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCBuZXh1cyBwcm9maWxlIGxvY2F0aW9uIGVtYWlsIiwic2lkIjoiNzgyYTUwNGItYWRkYi00NjYwLTllOWQtZDQ5ZjhiNDgwMjliIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5hbWUiOiJKZWFuLURlbmlzIENvdXJjb2wiLCJsb2NhdGlvbiI6IkIxIDUgMjczLjA1MCIsInByZWZlcnJlZF91c2VybmFtZSI6ImNvdXJjb2wiLCJnaXZlbl9uYW1lIjoiSmVhbi1EZW5pcyIsImZhbWlseV9uYW1lIjoiQ291cmNvbCIsImVtYWlsIjoiamVhbi1kZW5pcy5jb3VyY29sQGVwZmwuY2gifQ.NoVTBoUPGm8coMibuXXJyG9N5f5eomc6xx9EHbOzn3ippRAlFPcN2HfEr1VXwQ-aGnwxZE-OXbx8INgABInTgpWiNdnmWRXPyzeoPo2eE7AIs2WMmOWto0qVNThbXmn_aaaGWzaRzZSfgEuohUVQFmz_AQAKt7PQ5Q6i5LB8WC0PbK30fFq9AEhbI7O0aUAZ8cD_SRiSjqhxC4bEh19-Xk-ZpaxIRnrOmOYo3AuZsR4K9NTlW5Jg319af0xG6eIJ96bp43A3kR23rFLj2MVHaDj1_pTti_GJkanPgrJsHHRDE_0U8k5XtZMPrr7vEMzZko4IDLX1dPBMmrX4u3flYA"
#                   )
# app.run()