from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import UserProfile, RegistrationToken
from .serializers import UserRegistrationSerializer

# Create your views here.

class UserRegistrationView(APIView):
    USER_NOT_FOUND_ERROR_MESSAGE = 'User not found'
    USER_ALREADY_ACTIVE_ERROR_MESSAGE = 'User is already Active'
    USER_TOKEN_MISMATCH_ERROR_MESSAGE = 'Invalid token. Token in request does not match the token generated for this user.'
    TOKE_NOT_FOUND_ERROR_MESSAGE = 'Token not found.'
    INTERNAL_SERVER_ERROR_MESSAGE = 'Something went wrong : {0}'
    EXPECTED_KEY_NOT_PRESENT_IN_REQUEST = 'Key not present in request : {0}'
    ERROR_STATUS = {
        USER_NOT_FOUND_ERROR_MESSAGE : status.HTTP_404_NOT_FOUND,
        USER_ALREADY_ACTIVE_ERROR_MESSAGE : status.HTTP_400_BAD_REQUEST,
        USER_TOKEN_MISMATCH_ERROR_MESSAGE : status.HTTP_400_BAD_REQUEST,
        TOKE_NOT_FOUND_ERROR_MESSAGE : status.HTTP_404_NOT_FOUND,
        INTERNAL_SERVER_ERROR_MESSAGE : status.HTTP_500_INTERNAL_SERVER_ERROR,
        EXPECTED_KEY_NOT_PRESENT_IN_REQUEST : status.HTTP_400_BAD_REQUEST
    }

    def post(self, request, format=None):
        res_status = None
        error = None
        req = request.data
        try:
            user_queryset = User.objects.filter(email=req['user']['email'])
            result = self.__validate_request(user_queryset, req['token'])
            if 'error' in result:
                return Response({'error': result['error']}, status=result['status'])
            user = result['user']
            serializer = UserRegistrationSerializer(user,data=req['user'])
            if serializer.is_valid():
                serializer.save()
                self.__activate_user(user.userprofile)
                self.__mark_token_used(result['token'])
                res_status = status.HTTP_201_CREATED
            else:
                error = serializer.errors
                res_status = status.HTTP_400_BAD_REQUEST
        except KeyError as key_error:
            error = self.EXPECTED_KEY_NOT_PRESENT_IN_REQUEST.format(key_error)
            res_status = self.ERROR_STATUS[self.EXPECTED_KEY_NOT_PRESENT_IN_REQUEST]
        except Exception as e:
            error = self.INTERNAL_SERVER_ERROR_MESSAGE.format(e)
            res_status = self.ERROR_STATUS[self.INTERNAL_SERVER_ERROR_MESSAGE]
        return Response({'error': error}, status=res_status)

    def __validate_request(self, user_queryset, request_token):
        if not user_queryset.exists():
            return self.__build_error_result(self.USER_NOT_FOUND_ERROR_MESSAGE)
        user = user_queryset.first()
        if not user.userprofile.is_new():
            return self.__build_error_result(self.USER_ALREADY_ACTIVE_ERROR_MESSAGE)
        token_qs = RegistrationToken.objects.filter(token=request_token, used=False)
        if token_qs.exists():
            token = token_qs.first()
            if not (token and token.user.email == user.email):
                return self.__build_error_result(self.USER_TOKEN_MISMATCH_ERROR_MESSAGE)
        else:
            return self.__build_error_result(self.TOKE_NOT_FOUND_ERROR_MESSAGE)
        return {'user' : user, 'token' : token}

    def __build_error_result(self, error):
        return {'error' : error, 'status' : self.ERROR_STATUS[error]}

    def __activate_user(self, userprofile):
        userprofile.activate()
        userprofile.save()

    def __mark_token_used(self, token):
        token.mark_as_used()
        token.save()

