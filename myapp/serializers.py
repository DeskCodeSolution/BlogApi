from .models import *
from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id','username', 'email', 'password')

        extra_kwargs = {
            'password':{
                'write_only':True,
                'min_length':5
            }
        }

    def create(self, validated_data):
        print("validated data>>>", validated_data)
        user = User.objects.create_user(
            username = validated_data['username'],
            email=validated_data['email'],
            password = validated_data['password']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password')

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id','name',)

class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id','content', 'created_at', 'post', 'author')

class PostsListCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('id', 'title','updated_at','created_at', 'content', 'author', 'status', 'category')



class PostDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('id', 'title', 'content', 'status', 'category')

    def update(self, instance, validated_data):
        print("validated_data in detail post", validated_data)
        category_data = validated_data.pop('category', [])
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.status = validated_data.get('status', instance.status)
        instance.save()
        instance.category.set(category_data)
        return instance










