from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import (
    BrowsableAPIRenderer,
    JSONRenderer,
    HTMLFormRenderer,
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from .models import Incident, StatusType, SeverityType
from django.contrib.auth.models import User, Group
from .serializers import (
    IncidentSerializer,
    ReporterSerializer,
    IncidentCommentSerializer,
)
from .services import (
    get_incident_by_id,
    create_incident_postscript,
    update_incident_status,
    update_incident_severity,
    get_reporter_by_id,
    get_comments_by_incident,
    create_incident_comment_postscript,
    incident_auto_assign,
    incident_escalate
)


class IncidentResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "pageSize"
    max_page_size = 100


class IncidentList(APIView, IncidentResultsSetPagination):
    # authentication_classes = (JSONWebTokenAuthentication, )
    # permission_classes = (IsAuthenticated,)

    serializer_class = IncidentSerializer

    def get_paginated_response(self, data):
        return Response(
            dict(
                [
                    ("pages", self.page.paginator.num_pages),
                    ("pageNumber", self.page.number),
                    ("incidents", data),
                ]
            )
        )

    def get(self, request, format=None):
        incidents = Incident.objects.all()
    
        # filtering
        param_category = self.request.query_params.get('category', None)
        if param_category is not None:
            incidents = incidents.filter(category=param_category)

        param_start_date = self.request.query_params.get('start_date', None)
        param_end_date = self.request.query_params.get('end_date', None)

        if param_start_date and param_end_date:
            incidents = incidents.filter(created_date__range=(param_start_date, param_end_date))

        param_status = self.request.query_params.get('status', None)
        if param_status is not None:
            try:
                status_type = StatusType[param_status]
                incidents = [incident for incident in incidents if incident.current_status == status_type.name]
            except Exception as e:
                return Response("Invalid status", status=status.HTTP_400_BAD_REQUEST)
        
        param_severity = self.request.query_params.get('severity', None)
        if param_severity is not None:
            try:
                severity_type = SeverityType[param_severity]
                incidents = [incident for incident in incidents if incident.current_severity == severity_type.name]
            except Exception as e:
                return Response("Invalid severity", status=status.HTTP_400_BAD_REQUEST)

        results = self.paginate_queryset(incidents, request, view=self)
        serializer = IncidentSerializer(results, many=True)
        return self.get_paginated_response(serializer.data)

    def post(self, request, format=None):
        serializer = IncidentSerializer(data=request.data)
        if serializer.is_valid():
            incident = serializer.save()
            create_incident_postscript(incident, request.user)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentDetail(APIView):
    serializer_class = IncidentSerializer

    def get(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)

        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        serializer = IncidentSerializer(incident)
        return Response(serializer.data)

    def put(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)
        serializer = IncidentSerializer(incident, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentStatusView(APIView):
    def get(self, request, incident_id, format=None):
        if not (
            request.user.has_perm("incidents.can_request_status_change")
            or request.user.has_perm("incidents.can_change_status")
        ):
            return Response("Unauthorized", status=status.HTTP_401_UNAUTHORIZED)

        action = request.GET.get("action")

        incident = get_incident_by_id(incident_id)

        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        if action:
            if action == "update":
                status_type = request.GET.get("type")
                result = update_incident_status(incident, request.user, status_type)

                if result[0] == "success":
                    return Response(result[1])
                elif result[0] == "error":
                    return Response(result[1], status=status.HTTP_400_BAD_REQUEST)

            return Response("Invalid action", status=status.HTTP_400_BAD_REQUEST)
        return Response("No action defined", status=status.HTTP_400_BAD_REQUEST)


class IncidentSeverityView(APIView):
    def get(self, request, incident_id, format=None):
        if not (
            request.user.has_perm("incidents.can_request_severity_change")
            or request.user.has_perm("incidents.can_change_severity")
        ):
            return Response("Unauthorized", status=status.HTTP_401_UNAUTHORIZED)

        action = request.GET.get("action")

        incident = get_incident_by_id(incident_id)

        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        if action:
            if action == "update":
                severity_type = request.GET.get("type")
                result = update_incident_severity(incident, request.user, severity_type)

                if result[0] == "success":
                    return Response(result[1])
                elif result[0] == "error":
                    return Response(result[1], status=status.HTTP_400_BAD_REQUEST)

            return Response("Invalid action", status=status.HTTP_400_BAD_REQUEST)
        return Response("No action defined", status=status.HTTP_400_BAD_REQUEST)


class ReporterDetail(APIView):
    serializer_class = ReporterSerializer

    def get(self, request, reporter_id, format=None):
        reporter = get_reporter_by_id(reporter_id)

        if reporter is None:
            return Response("Invalid reporter id", status=status.HTTP_404_NOT_FOUND)

        serializer = ReporterSerializer(reporter)
        return Response(serializer.data)

    def put(self, request, reporter_id, format=None):
        snippet = get_reporter_by_id(reporter_id)
        serializer = ReporterSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentCommentView(APIView):
    serializer_class = IncidentCommentSerializer

    def get(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)
        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        comments = get_comments_by_incident(incident)
        serializer = IncidentCommentSerializer(comments)
        return Response(serializer.data)

    def post(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)
        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        comment_data = request.data
        comment_data["incident"] = incident.id
        serializer = IncidentCommentSerializer(data=comment_data)
        if serializer.is_valid():
            comment = serializer.save()
            create_incident_comment_postscript(incident, request.user, comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IncidentSearchByStatus(APIView):
    serializer_class = IncidentSerializer

    def get(self, request, format=None):
        status_type = request.GET.get("type")

        if status_type:
            filtered_incidents = get_incidents_by_status(status_type)
            serializer = IncidentSerializer(filtered_incidents, many=True)
            return Response(serializer.data)

        return Response("Status type is invalid or not defined", status=status.HTTP_400_BAD_REQUEST)


class IncidentEscalateView(APIView):
    def get(self, request, incident_id, format=None):
        incident = get_incident_by_id(incident_id)
        if incident is None:
            return Response("Invalid incident id", status=status.HTTP_404_NOT_FOUND)

        result = incident_escalate(request.user, incident)
        if result[0] == 'success':
            return Response("Incident escalated", status=status.HTTP_200_OK)
        
        return Response(result[1], status=status.HTTP_400_BAD_REQUEST)
