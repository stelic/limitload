#ifndef EXPIMP_H
#define EXPIMP_H

#if 1
    #define DECLARE_TYPE_HANDLE(name) \
        public: \
            static TypeHandle get_class_type() { \
                return _type_handle; \
            } \
            static void init_type() { \
                TypedObject::init_type(); \
                register_type(_type_handle, #name, \
                              TypedObject::get_class_type()); \
            } \
            virtual TypeHandle get_type() const { \
                return get_class_type(); \
            } \
            virtual TypeHandle force_init_type() { \
                init_type(); \
                return get_class_type(); \
            } \
        private: \
            static TypeHandle _type_handle;

    #define INITIALIZE_TYPE_HANDLE(name) \
        TypeHandle name::_type_handle;

    #define INITIALIZE_TYPE(name) \
        name::init_type();
#else
    #define DECLARE_TYPE_HANDLE(name)
    #define INITIALIZE_TYPE_HANDLE(name)
    #define INITIALIZE_TYPE(name)
#endif

#endif
