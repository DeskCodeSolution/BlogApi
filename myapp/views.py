from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .models import *
from .serializers import *
from drf_spectacular.utils import extend_schema
from .permissions import UpdateOwnPosts
from app import settings
from rest_framework import generics
from django.core.cache import cache
import time

from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework import filters
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


from rest_framework_simplejwt.tokens import RefreshToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    # print("refresh token>>", refresh)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

import jwt
from jwt.exceptions import ExpiredSignatureError, DecodeError
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes


def decode_access_token(token):
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])  # 'HS256' ko apne algorithm ke hisaab se set karein
        return decoded_token
    except ExpiredSignatureError:
        return {'error': 'Token has expired'}
    except DecodeError:
        return {'error': 'Failed to decode token'}
    except jwt.InvalidTokenError:
            return Response({'error': 'Invalid token'}, status=401)



########### User Registration ############

class UserRegisterView(APIView):
    @extend_schema(
    tags=['user'],
    request=UserSerializer,
    responses={201: {"Success":"user Created Successfully"}}
    )

    def post(self, request):
        print("user register data>>>", request.data)
        serializer = UserSerializer(data = request.data)

        if serializer.is_valid():

            serializer.save()
            return Response({'success':'user registered'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

################ User Login ##################

class UserLoginView(APIView):

    @extend_schema(
    tags=['user'],
    request=LoginSerializer,
    )

    def post(self, request):
        count = 0
        user_key = request.META.get('REMOTE_ADDR')
        key = f'throttle_{user_key}'
        data = cache.get(key, [])
        now = time.time()
        data = [t for t in data if now - t < 60]
        if len(data) >= 3:
            return Response(
                {"detail": "Too many requests."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        data.append(now)
        cache.set(key, data, timeout=60)
        count=count+1
        print('cache>>>', cache)
        print("<<<counting>>>", count)

        username = request.data.get('username')
        password = request.data.get('password')

        print("username in login",username, password)
        try:
            user = User.objects.get(username = username)
            # print("before check password for user>>>", user)
        except User.DoesNotExist:
            return Response({"msg":"user with these username does not exists"}, status=status.HTTP_404_NOT_FOUND)

        if user.check_password(password):
            print("user returned while login>>", user)
            refresh = RefreshToken.for_user(user)
            print("refresh>>>>", refresh)
            token = {
                'refresh':str(refresh),
                'access':str(refresh.access_token)
            }
            return Response({'success':'user login successfully', 'tokens':token}, headers={
            "Authorize":token
        })

        return Response({"msg":"given password is not valid"}, status=status.HTTP_404_NOT_FOUND)


######### PostView ########

class Pagination(PageNumberPagination):
    page_size_query_param = 'per_page_records'
    max_page_size = 10

######## posts searching and ordering #############

class PostsListCreateView(APIView):

    permission_classes = [IsAuthenticatedOrReadOnly,]
    # pagination_class = Pagination
    pagination_class = LimitOffsetPagination
    throttle_classes = [AnonRateThrottle, UserRateThrottle,]

    @extend_schema(
        tags=['posts'],
        parameters=[
            OpenApiParameter(name='search', description='Search in title', type=str),
            OpenApiParameter(name='ordering', description='Order by field (author, created_at) with optional dsc prefix for descending', type=str),
        ],
        responses={200: PostsListCreateSerializer(many=True)},
        description="Search and filter posts with pagination"
    )
    def get(self, request):
        queryset = Post.objects.all()
        search_term = request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term)|
                Q(content__icontains=search_term)
            )
        ordering = request.query_params.get('ordering')
        print("ordering in>>>>", ordering)

        if ordering:
            if ordering.startswith('dsc'):
                ordering_field = ordering[4:]
                print("ordering_fields>>>",ordering_field)

                if ordering_field in ['author', 'created_at']:
                    queryset = queryset.order_by('-' + ordering_field)
            else:
                if ordering in ('author', 'created_at'):
                    queryset = queryset.order_by(ordering)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = PostsListCreateSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = PostsListCreateSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
    tags=['posts'],
    request=PostsListCreateSerializer,
    responses={201: {"Success":"post Created Successfully"}}
    )

    def post(self, request):

        auth_header = request.headers.get('Authorization')
        token_name, token = auth_header.split(" ")

        decoded_token = decode_access_token(token)
        if 'error' not in decoded_token:
            user_id = decoded_token.get('user_id')
            user = User.objects.get(id = user_id)

        data = request.data
        data['author'] = request.user.id
        serializer = PostsListCreateSerializer(data = data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success":"data posted successfully"}, status=status.HTTP_201_CREATED)
        return Response({"msg":serializer.errors})


class PostsDetailView(APIView):

    permission_classes = [UpdateOwnPosts,]

    @extend_schema(
    tags=['posts'],
    request=PostsListCreateSerializer,
    responses={200: {"Success":"post get  Successfully"}}
    )

    def get(self,request,pk):
        print("post_id>>",pk)
        # return Response({"msg":"found"})
        try:
            post = Post.objects.get(id = pk  )

            serializer = PostsListCreateSerializer(post)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"msg":"record not found"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
    tags=['posts'],
    request=PostDetailSerializer,
    responses={200: {"Success":"put Successfully"}},
    )
    def put(self, request, pk):
        try:
            post = Post.objects.get(id=pk)
            self.check_object_permissions(request, post)

            data = request.data
            data['author'] = request.user.id
            serializer = PostDetailSerializer(post, data=data)
            if serializer.is_valid():
                serializer.save()
                return Response({"msg":"updated"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Post.DoesNotExist:
            return Response({"msg":"record not found"}, status=status.HTTP_404_NOT_FOUND)


    @extend_schema(
            tags=['posts'],
    )

    def delete(self, request, pk):
        try:
            post = Post.objects.get(id = pk)
            # Check permissions explicitly
            self.check_object_permissions(request, post)
            post.delete()
            return Response({"msg":"post deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Post.DoesNotExist:
            return Response({"msg":"record not found"}, status=status.HTTP_404_NOT_FOUND)

########### Creating and Retriving Comments ###############

class CommentCreateView(APIView):

    permission_classes = [IsAuthenticated,]


    @extend_schema(
    tags=['comment'],
    request= CommentCreateSerializer,
    responses={201: {"Success":"post Successfully"}}
    )

    def post(self, request):
        data = request.data
        data['author'] = request.user.id
        print("comment create data>>>:", data)
        serializer = CommentCreateSerializer(data = data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success":"comment successfully created"}, status=status.HTTP_201_CREATED)
        return Response({"msg":serializer.errors})

    @extend_schema(
    tags=['comment'],
    request= CommentCreateSerializer,
    responses={200: {"Success":"get Successfully"}}
    )
    def get(self, request):
        queryset = Comment.objects.all()
        serializer = CommentCreateSerializer(queryset, many = True)
        return Response(serializer.data)



class CategoryCreateView(APIView):

    permission_classes = [IsAuthenticated,]

    @extend_schema(
    tags=['category'],
    request= CategorySerializer,
    responses={200: {"Success":"post Successfully"}}
    )

    def post(self, request):
        serializer = CategorySerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"msg":"category created"})
        return Response({"msg":serializer.errors})

    @extend_schema(
    tags=['category'],
    request= CategorySerializer,
    responses={200: {"Success":"get Successfully"}}
    )
    def get(self, request):
        queryset = Category.objects.all()
        serializer = CategorySerializer(queryset, many = True)
        return Response(serializer.data)


class CategoryPostList(APIView):

    @extend_schema(
    tags=['category'],
    request= CategorySerializer,
    responses={200: {"Success":"post Successfully"}}
    )

    def get(self, request, name):
        try:
            category = Category.objects.get(name = name)
            if category:
                posts = Post.objects.filter(category=category.id)
                serializer = PostsListCreateSerializer(posts, many=True)
                return Response(serializer.data)
        except Category.DoesNotExist:
            return Response({'msg':'posts with the given category does not exists'}, status=status.HTTP_404_NOT_FOUND)












